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

import math
from PyPDF2 import PdfFileWriter
from PyQt5.QtCore import Qt, QMetaObject, QRunnable, Q_ARG
from PyQt5.QtGui import QTransform

class PDFExportOperation(QRunnable):
    def __init__(self, inPage, outFileName, cropOrig, cropSize,
                 outSize, pageSize, pageMargin, progress=None):
        super(PDFExportOperation, self).__init__()

        self.inPage = inPage
        self.outFileName = outFileName
        self.outSize = outSize
        self.pageSize = pageSize
        self.pageMargin = pageMargin

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
        outPDF = PdfFileWriter()

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
                page.mergeTransformedPage(self.inPage.getPDFReaderPage(), ctm)

        self._reportProgress(self.numPagesX * self.numPagesY)

        with open(self.outFileName, 'wb') as f:
            outPDF.write(f)

        self._reportProgress(self.numPagesX * self.numPagesY + 1)
