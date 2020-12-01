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
from PyQt5.QtCore import Qt, QMetaObject, QRunnable, Q_ARG
from PyQt5.QtGui import QTransform

class PDFExportOperation(QRunnable):
    def __init__(self, inPage, outFileName, cropOrig, cropSize,
                 outSize, pageSize, pageMargin,
                 registrationMarks=False, progress=None):
        super(PDFExportOperation, self).__init__()

        self.inPage = inPage
        self.outFileName = outFileName
        self.outSize = outSize
        self.pageSize = pageSize
        self.pageMargin = pageMargin
        self.registrationMarks = registrationMarks

        self.printableWidth = pageSize[0] - 2 * pageMargin[0]
        self.printableHeight = pageSize[1] - 2 * pageMargin[1]

        # Compute the transform in global space
        self.globalXform = QTransform()
        self.globalXform.scale(outSize[0] / cropSize[0],
                               outSize[1] / cropSize[1])
        self.globalXform.translate(-cropOrig[0], -cropOrig[1])

        self.numPagesX = math.ceil(outSize[0] / self.printableWidth)
        self.numPagesY = math.ceil(outSize[1] / self.printableHeight)

        self.progress = progress
        if self.progress:
            self.progress.setMaximum(self.numPagesX * self.numPagesY + 1)

    def wasCanceled(self):
        return self.progress and self.progress.wasCanceled()

    def _reportProgress(self, p):
        if self.progress:
            QMetaObject.invokeMethod(self.progress, "setValue",
                                     Qt.QueuedConnection,
                                     Q_ARG(int, p))

    def run(self):
        if isinstance(self.inPage, InputPDFPage):
            inReaderPage = self.inPage.getPDFReaderPage()
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
        if self.registrationMarks:
            pdf = fpdf.FPDF(unit='pt', format=self.pageSize)
            pdf.add_page()
            pw = self.pageSize[0]
            ph = self.pageSize[1]
            mw = self.pageMargin[0]
            mh = self.pageMargin[1]
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

                self._reportProgress(self.numPagesX * y + x)

                xt = x * self.printableWidth
                yt = y * self.printableHeight

                # PDF coordinates start at the bottom-left but most people
                # think top-down so flip the Y transform
                yt = self.outSize[1] - yt - self.printableHeight

                pageXform = QTransform()
                pageXform.translate(self.pageMargin[0], self.pageMargin[1])
                pageXform.translate(-xt, -yt)
                pageXform = self.globalXform * pageXform
                assert pageXform.isAffine()
                ctm = (
                    pageXform.m11(),
                    pageXform.m12(),
                    pageXform.m21(),
                    pageXform.m22(),
                    pageXform.m31(),
                    pageXform.m32()
                )
                page = outPDF.addBlankPage(self.pageSize[0], self.pageSize[1])
                page.mergeTransformedPage(inReaderPage, ctm)

                if overlayPage:
                    page.mergePage(overlayPage)

        self._reportProgress(self.numPagesX * self.numPagesY)

        with open(self.outFileName, 'wb') as f:
            outPDF.write(f)

        self._reportProgress(self.numPagesX * self.numPagesY + 1)
