# Copyright © 2020 Jason Ekstrand
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import fpdf
from inputPDF import InputPDFPage
from inputImage import InputImage
import io
import math
import PyPDF2
from PyQt5.QtCore import Qt, QMetaObject, QRunnable, QSize, Q_ARG
from PyQt5.QtGui import QBrush, QPageSize, QPainter, QPen, QTransform
from PyQt5.QtPrintSupport import QPrinter

class OutputOperation(QRunnable):
    def __init__(self, inPage, cropOrig, cropSize,
                 outSize, pageSize, pageMargin, trim=False,
                 registrationMarks=False, progress=None):
        super(OutputOperation, self).__init__()

        self.inPage = inPage
        self.cropOrig = cropOrig
        self.cropSize = cropSize
        self.outSize = outSize
        self.pageSize = pageSize
        self.pageMargin = pageMargin
        self.trim = trim
        self.registrationMarks = registrationMarks

        self.printableWidth = pageSize[0] - 2 * pageMargin[0]
        self.printableHeight = pageSize[1] - 2 * pageMargin[1]

        self.numPagesX = math.ceil(outSize[0] / self.printableWidth)
        self.numPagesY = math.ceil(outSize[1] / self.printableHeight)

        self.progress = progress
        if self.progress:
            self.progress.setMaximum(self.numPagesX * self.numPagesY + 1)

    def wasCanceled(self):
        return self.progress and self.progress.wasCanceled()

    def reportProgress(self, p):
        if self.progress:
            QMetaObject.invokeMethod(self.progress, "setValue",
                                     Qt.QueuedConnection,
                                     Q_ARG(int, p))

    def drawInputImage(self, painter, xt, yt):
        painter.save()

        if self.trim:
            painter.setClipRect(self.pageMargin[0],
                                self.pageMargin[1],
                                self.printableWidth,
                                self.printableHeight)

        painter.translate(self.pageMargin[0], self.pageMargin[1])
        painter.translate(-xt, -yt)
        painter.scale(self.outSize[0] / self.cropSize[0],
                      self.outSize[1] / self.cropSize[1])
        painter.translate(-self.cropOrig[0], -self.cropOrig[1])

        # Ask the back-end to scale the image.  It may not.
        preferredScale = max(painter.device().physicalDpiX() / 72,
                             painter.device().physicalDpiY() / 72)
        image = self.inPage.getQImage(preferredScale)

        # Figure out the actual scale
        painter.scale(self.inPage.getSize()[0] / image.size().width(),
                      self.inPage.getSize()[1] / image.size().height())
        painter.drawImage(0, 0, image)

        painter.restore()

    def drawWhiteBorder(self, painter):
        pw = self.pageSize[0]
        ph = self.pageSize[1]
        mw = self.pageMargin[0]
        mh = self.pageMargin[1]

        painter.save()
        painter.setBrush(QBrush(Qt.white))
        painter.setPen(QPen(Qt.NoPen))
        painter.drawRect(0, 0, mw, ph, 'F')
        painter.drawRect(0, 0, pw, mh, 'F')
        painter.drawRect(pw - mw, 0, mw, ph, 'F')
        painter.drawRect(0, ph - mh, pw, mh, 'F')
        painter.restore()

    def drawRegistrationMarks(self, painter):
        pw = self.pageSize[0]
        ph = self.pageSize[1]
        mw = self.pageMargin[0]
        mh = self.pageMargin[1]

        # A caution factor of 90% to keep our registration lines from
        # running into the main page area
        cf = 0.9

        pen = QPen()
        pen.setStyle(Qt.SolidLine)
        pen.setWidth(1)
        pen.setBrush(Qt.black)

        painter.save()
        painter.setPen(pen)
        painter.drawLine(0, mh, mw * cf, mh)
        painter.drawLine(mw, 0, mw, mh * cf)
        painter.drawLine(pw, mh, pw - mw * cf, mh)
        painter.drawLine(pw - mw, 0, pw - mw, mh * cf)
        painter.drawLine(0, ph - mh, mw * cf, ph - mh)
        painter.drawLine(mw, ph, mw, ph - mh * cf)
        painter.drawLine(pw, ph - mh, pw - mw * cf, ph - mh)
        painter.drawLine(pw - mw, ph, pw - mw, ph - mh * cf)
        painter.restore()

    def setupPrinterPainter(self, printer):
        printerMargins = printer.pageLayout().marginsPoints()
        if printerMargins.left() > self.pageMargin[0] or \
           printerMargins.right() > self.pageMargin[0] or \
           printerMargins.top() > self.pageMargin[1] or \
           printerMargins.bottom() > self.pageMargin[1]:
            print("WARNING: Printer margins are larger than page margins")

        fullRect = printer.pageLayout().fullRectPoints()
        if fullRect.width() < self.pageSize[0] or \
           fullRect.height() < self.pageSize[1]:
            print("WARNING: Printer page size is smaller than configured")

        printer.setFullPage(True)

        painter = QPainter()
        if not painter.begin(printer):
            raise RuntimeError("Failed to open printer, is it writable?")

        pageSizeQtLogical = (
            self.pageSize[0] * printer.logicalDpiX() / 72,
            self.pageSize[1] * printer.logicalDpiY() / 72,
        )
        painter.setRenderHint(QPainter.LosslessImageRendering, True)
        painter.setWindow(0, 0, self.pageSize[0], self.pageSize[1])
        painter.setViewport(0, 0, pageSizeQtLogical[0], pageSizeQtLogical[1])

        return painter


class PDFExportOperation(OutputOperation):
    def __init__(self, outFileName, *args, **kwargs):
        super(PDFExportOperation, self).__init__(*args, **kwargs)

        self.outFileName = outFileName

    def run(self):
        if isinstance(self.inPage, InputPDFPage):
            inReaderPage = self.inPage.getPyPDF2PageObject()
        elif isinstance(self.inPage, InputImage):
            # If inPage is an image, turn it into a PDF first.  No,
            # this isn't the most efficient thing in the world to do
            # but it works and makes everything simpler.
            inputSize = self.inPage.getSize()
            pdf = fpdf.FPDF(unit='pt', format=inputSize)
            pdf.add_page()
            pdf.image(self.inPage.tmpFileName,
                      0, 0, inputSize[0], inputSize[1])
            data = pdf.output(dest='S').encode('latin-1')
            reader = PyPDF2.PdfFileReader(io.BytesIO(data))
            inReaderPage = reader.getPage(0)
        else:
            raise TypeError("Invalid page type")

        overlayPage = None
        if self.trim or self.registrationMarks:
            pdf = fpdf.FPDF(unit='pt', format=self.pageSize)
            pdf.add_page()
            pw = self.pageSize[0]
            ph = self.pageSize[1]
            mw = self.pageMargin[0]
            mh = self.pageMargin[1]

            # We "trim" the page by rendering white in the margins
            if self.trim:
                pdf.set_fill_color(255)
                pdf.rect(0, 0, mw, ph, 'F')
                pdf.rect(0, 0, pw, mh, 'F')
                pdf.rect(pw - mw, 0, mw, ph, 'F')
                pdf.rect(0, ph - mh, pw, mh, 'F')

            if self.registrationMarks:
                # A caution factor of 90% to keep our registration lines from
                # running into the main page area
                cf = 0.9
                pdf.line(0, mh, mw * cf, mh)
                pdf.line(mw, 0, mw, mh * cf)
                pdf.line(pw, mh, pw - mw * cf, mh)
                pdf.line(pw - mw, 0, pw - mw, mh * cf)
                pdf.line(0, ph - mh, mw * cf, ph - mh)
                pdf.line(mw, ph, mw, ph - mh * cf)
                pdf.line(pw, ph - mh, pw - mw * cf, ph - mh)
                pdf.line(pw - mw, ph, pw - mw, ph - mh * cf)

            data = pdf.output(dest='S').encode('latin-1')
            reader = PyPDF2.PdfFileReader(io.BytesIO(data))
            overlayPage = reader.getPage(0)

        outPDF = PyPDF2.PdfFileWriter()

        for y in range(self.numPagesY):
            for x in range(self.numPagesX):
                if self.wasCanceled():
                    return

                self.reportProgress(self.numPagesX * y + x)

                xt = x * self.printableWidth
                yt = y * self.printableHeight

                # PDF coordinates start at the bottom-left but everything
                # else is top-down so flip the Y transform
                yt = self.outSize[1] - yt - self.printableHeight

                xform = QTransform()
                xform.translate(self.pageMargin[0], self.pageMargin[1])
                xform.translate(-xt, -yt)
                xform.scale(self.outSize[0] / self.cropSize[0],
                            self.outSize[1] / self.cropSize[1])
                xform.translate(-self.cropOrig[0], -self.cropOrig[1])
                assert xform.isAffine()
                ctm = (
                    xform.m11(),
                    xform.m12(),
                    xform.m21(),
                    xform.m22(),
                    xform.m31(),
                    xform.m32()
                )
                page = outPDF.addBlankPage(self.pageSize[0], self.pageSize[1])
                page.mergeTransformedPage(inReaderPage, ctm)

                if overlayPage:
                    page.mergePage(overlayPage)

        self.reportProgress(self.numPagesX * self.numPagesY)

        with open(self.outFileName, 'wb') as f:
            outPDF.write(f)

        self.reportProgress(self.numPagesX * self.numPagesY + 1)

class PrintOperation(OutputOperation):
    def __init__(self, *args, **kwargs):
        super(PrintOperation, self).__init__(*args, **kwargs)

        self.printer = QPrinter()
        self.printer.setColorMode(QPrinter.Color)
        qPageSize = QPageSize(QSize(self.pageSize[0], self.pageSize[1]))
        self.printer.setPageSize(qPageSize)

    def getNumPages(self):
        return self.numPagesX * self.numPagesY

    def run(self):
        painter = self.setupPrinterPainter(self.printer)

        for y in range(self.numPagesY):
            for x in range(self.numPagesX):
                if self.wasCanceled():
                    return

                self.reportProgress(self.numPagesX * y + x)

                if x > 0 or y > 0:
                    if not self.printer.newPage():
                        raise RuntimeError("Failed to flush the page")

                xt = x * self.printableWidth
                yt = y * self.printableHeight
                self.drawInputImage(painter, xt, yt)

                if self.registrationMarks:
                    self.drawRegistrationMarks(painter)

        self.reportProgress(self.numPagesX * self.numPagesY + 1)
