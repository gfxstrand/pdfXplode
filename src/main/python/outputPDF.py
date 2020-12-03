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

from inputPDF import InputPDFPage
from inputImage import InputImage
import io
import math
import os
import PyPDF2
from PyQt5.QtCore import QPoint, QRect, QSize
from PyQt5.QtCore import (
    pyqtSignal,
    Qt,
    QMarginsF,
    QMetaObject,
    QObject,
    QRunnable,
    QThreadPool,
    Q_ARG
)
from PyQt5.QtGui import (
    QBrush,
    QPageLayout,
    QPageSize,
    QPainter,
    QPen,
    QTransform,
)
from PyQt5.QtPrintSupport import QPrinter
import tempfile

def _paintWhiteBorder(printer, painter):
    page = printer.pageLayout().fullRectPoints()
    margin = printer.pageLayout().marginsPoints()

    painter.save()
    painter.setBrush(QBrush(Qt.white))
    painter.setPen(QPen(Qt.NoPen))
    painter.drawRect(0, 0, margin.left(), page.height())
    painter.drawRect(0, 0, page.width(), margin.top())
    painter.drawRect(page.width() - margin.right(), 0,
                     margin.right(), page.height())
    painter.drawRect(0, page.height() - margin.bottom(),
                     page.width(), margin.bottom())
    painter.restore()


def _paintRegistrationMarks(printer, painter):
    page = printer.pageLayout().fullRectPoints()
    margin = printer.pageLayout().marginsPoints()

    # Get ourselves some nice abbreviations
    pw = page.width()
    ph = page.height()
    ml = margin.left()
    mr = margin.right()
    mt = margin.top()
    mb = margin.bottom()

    # A caution factor of 90% to keep our registration lines from
    # running into the main page area
    cf = 0.9

    pen = QPen()
    pen.setStyle(Qt.SolidLine)
    pen.setWidth(1)
    pen.setBrush(Qt.black)

    painter.save()
    painter.setPen(pen)
    painter.drawLine(0, mt, ml * cf, mt)
    painter.drawLine(ml, 0, ml, mt * cf)
    painter.drawLine(pw, mt, pw - mr * cf, mt)
    painter.drawLine(pw - mr, 0, pw - mr, mt * cf)
    painter.drawLine(0, ph - mb, ml * cf, ph - mb)
    painter.drawLine(ml, ph, ml, ph - mb * cf)
    painter.drawLine(pw, ph - mb, pw - mr * cf, ph - mb)
    painter.drawLine(pw - mr, ph, pw - mr, ph - mb * cf)
    painter.restore()


def _makePainter(printer):
    # We'll deal with margins ourselves, thank you.
    printer.setFullPage(True)

    painter = QPainter()
    if not painter.begin(printer):
        raise RuntimeError("Failed to open printer, is it writable?")

    painter.setRenderHint(QPainter.LosslessImageRendering, True)

    pageSizePoints = printer.pageLayout().fullRectPoints().size()
    pageSizeLogical = QSize(
        (pageSizePoints.width() * printer.logicalDpiX()) / 72,
        (pageSizePoints.height() * printer.logicalDpiY()) / 72)

    painter.setWindow(QRect(QPoint(0, 0), pageSizePoints))
    painter.setViewport(QRect(QPoint(0, 0), pageSizeLogical))

    return painter


def printOverlayPage(printer, trim=False, registrationMarks=False):
    painter = _makePainter(printer)

    if trim:
        _paintWhiteBorder(printer, painter)

    if registrationMarks:
        _paintRegistrationMarks(printer, painter)

    painter.end()


def printInputImage(printer, inPage, cropRect, outSize,
                    trim=False, registrationMarks=False,
                    progress=None):
    painter = _makePainter(printer)

    fullRect = printer.pageLayout().fullRectPoints()
    margin = printer.pageLayout().marginsPoints()

    printableWidth = fullRect.width() - margin.left() - margin.right()
    printableHeight = fullRect.height() - margin.top() - margin.bottom()

    numPagesX = math.ceil(outSize.width() / printableWidth)
    numPagesY = math.ceil(outSize.height() / printableHeight)
    numPages = numPagesX * numPagesY

    imageSizeHint = QSize(
        (inPage.getSize().width() *
         painter.device().physicalDpiX() *
         outSize.width()) /
        (cropRect.width() * 72),
        (inPage.getSize().height() *
         painter.device().physicalDpiY() *
         outSize.height()) /
        (cropRect.height() * 72))

    image = inPage.getQImage(imageSizeHint)

    for y in range(numPagesY):
        for x in range(numPagesX):
            percentComplete = ((numPagesX * y + x) * 100) // numPages
            if progress and not progress(percentComplete):
                printer.abort()
                return

            if x > 0 or y > 0:
                if not printer.newPage():
                    raise RuntimeError("Failed to flush the page")

            if registrationMarks:
                _paintRegistrationMarks(printer, painter)

            painter.save()

            if trim:
                painter.setClipRect(margin.left(), margin.top(),
                                    printableWidth, printableHeight)

            painter.translate(margin.left(), margin.top())
            painter.translate(-x * printableWidth, -y * printableHeight)
            painter.scale(outSize.width() / cropRect.width(),
                          outSize.height() / cropRect.height())
            painter.translate(-cropRect.x(), -cropRect.y())

            painter.scale(inPage.getSize().width() / image.size().width(),
                          inPage.getSize().height() / image.size().height())
            painter.drawImage(0, 0, image)

            painter.restore()

    painter.end()

    if progress:
        progress(100)


def generatePDF(fileName, inPage, cropRect, outSize,
                pageLayout, trim=False, registrationMarks=False,
                progress=None):
    if isinstance(inPage, InputImage):
        printer = QPrinter()
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(fileName)
        printer.setColorMode(QPrinter.Color)
        printer.setPageLayout(pageLayout)
        printInputImage(printer, inPage, cropRect, outSize,
                        trim, registrationMarks, progress)
        return

    inReaderPage = inPage.getPyPDF2PageObject()

    overlayPage = None
    if trim or registrationMarks:
        with tempfile.TemporaryDirectory(prefix='pdfXplode-tmpPDF') as d:
            # Print our trimming and registration marks to a temporary
            # PDF so we can merge it with the input PDF.  Sadly,
            # QPrinter has no way to print to an in-memory stream so we
            # have to use a temporary file.
            tmpFileName = os.path.join(d, 'overlay.pdf')

            printer = QPrinter()
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(tmpFileName)
            printer.setPageLayout(pageLayout)
            printOverlayPage(printer, trim, registrationMarks)

            with open(tmpFileName, 'rb') as f:
                overlayPDFBytes = f.read()

        reader = PyPDF2.PdfFileReader(io.BytesIO(overlayPDFBytes))
        overlayPage = reader.getPage(0)

    fullRect = printer.pageLayout().fullRectPoints()
    margin = printer.pageLayout().marginsPoints()

    printableWidth = fullRect.width() - margin.left() - margin.right()
    printableHeight = fullRect.height() - margin.top() - margin.bottom()

    numPagesX = math.ceil(outSize.width() / printableWidth)
    numPagesY = math.ceil(outSize.height() / printableHeight)
    numPages = numPagesX * numPagesY

    outPDF = PyPDF2.PdfFileWriter()

    for y in range(numPagesY):
        for x in range(numPagesX):
            percentComplete = ((numPagesX * y + x) * 100) // (numPages + 1)
            if progress and not progress(percentComplete):
                return

            xt = x * printableWidth
            yt = y * printableHeight

            # PDF coordinates start at the bottom-left but everything
            # else is top-down so flip the Y transform
            yt = outSize.height() - yt - printableHeight

            xform = QTransform()
            xform.translate(margin.left(), margin.bottom())
            xform.translate(-xt, -yt)
            xform.scale(outSize.width() / cropRect.width(),
                        outSize.height() / cropRect.height())
            xform.translate(-cropRect.x(), -cropRect.y())
            assert xform.isAffine()
            ctm = (
                xform.m11(),
                xform.m12(),
                xform.m21(),
                xform.m22(),
                xform.m31(),
                xform.m32()
            )
            page = outPDF.addBlankPage(fullRect.width(), fullRect.height())
            page.mergeTransformedPage(inReaderPage, ctm)

            if overlayPage:
                page.mergePage(overlayPage)

    if progress:
        progress((numPages * 100) // (numPages + 1))

    with open(fileName, 'wb') as f:
        outPDF.write(f)

    if progress:
        progress(100)


class ThreadedOperationRunnable(QRunnable):
    progress = pyqtSignal(int)

    def __init__(self, func, *args, **kwargs):
        super(ThreadedOperationRunnable, self).__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        self.func(*self.args, **self.kwargs)


class ThreadedOperation(QObject):
    progress = pyqtSignal(int)

    def __init__(self, func, *args, **kwargs):
        super(ThreadedOperation, self).__init__()

        # Patch through our own _reportProgress which marshals through Qt
        # threads so we end up with the signal happening on the UI thread.
        assert 'progress' not in kwargs
        kwargs['progress'] = self._reportProgress

        self._runnable = ThreadedOperationRunnable(func, *args, **kwargs)
        self._canceled = False

    def _reportProgress(self, p):
        QMetaObject.invokeMethod(self, "progress",
                                 Qt.QueuedConnection,
                                 Q_ARG(int, p))
        return not self._canceled;

    def cancel(self):
        self._canceled = True

    def run(self):
        print("Running...")
        self._runnable.run()

    def runInThread(self):
        QThreadPool.globalInstance().start(self._runnable)


class PrintOperation(ThreadedOperation):
    def __init__(self, inPage, cropRect, outSize,
                 pageSize, pageMargin, trim=False,
                 registrationMarks=False, progress=None):
        # Convert to a Qt page layout
        pageSize = QPageSize(QSize(*pageSize))
        pageMargin = QMarginsF(*pageMargin, *pageMargin)
        pageLayout = QPageLayout(pageSize, QPageLayout.Portrait, pageMargin)

        printer = QPrinter()
        printer.setColorMode(QPrinter.Color)
        printer.setPageLayout(pageLayout)

        super(PrintOperation, self).__init__(printInputImage, printer,
                                             inPage, cropRect, outSize,
                                             trim, registrationMarks)

        self.printer = printer

        if progress:
            progress.setMaximum(100)
            progress.setValue(0)
            self.progress.connect(progress.setValue)
            progress.canceled.connect(self.cancel)


def PDFExportOperation(fileName, inPage, cropRect, outSize,
                       pageSize, pageMargin, trim=False,
                       registrationMarks=False, progress=None):
    # Convert to a Qt page layout
    pageSize = QPageSize(QSize(*pageSize))
    pageMargin = QMarginsF(*pageMargin, *pageMargin)
    pageLayout = QPageLayout(pageSize, QPageLayout.Portrait, pageMargin)

    op = ThreadedOperation(generatePDF, fileName, inPage, cropRect,
                           outSize, pageLayout, trim, registrationMarks)

    if progress:
        progress.setMaximum(100)
        progress.setValue(0)
        op.progress.connect(progress.setValue)
        progress.canceled.connect(op.cancel)

    return op
