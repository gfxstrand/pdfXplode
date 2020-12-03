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

import os
from popplerqt5 import Poppler
import PyPDF2
from PyQt5.QtCore import QSize
import shutil
import tempfile
import units

class InputPDFPage(object):
    def __init__(self, pdfFile, pageNumber):
        self.pdfFile = pdfFile
        self.pageNumber = pageNumber
        self.page = pdfFile.doc.page(pageNumber - 1)
        self._qImageSize = QSize(0, 0)
        self._qImage = None

    def cleanup(self):
        self._page = None
        self._qImage = None

    def getAllowedUnits(self):
        return [units.POINTS, units.INCHES]

    def getNativeUnit(self):
        return units.POINTS

    def getPyPDF2PageObject(self):
        return self.pdfFile.getPyPDF2Reader().getPage(self.pageNumber - 1)

    def getSize(self):
        return self.page.pageSize()

    def getQImage(self, sizeHint=None):
        if sizeHint == None:
            sizeHint = self.page.pageSize()

        assert sizeHint.width() > 1 and sizeHint.height() > 1

        if self._qImageSize != sizeHint:
            self._qImage = None

        while self._qImage is None:
            xDpi = (sizeHint.width() * 72) / self.page.pageSizeF().width()
            yDpi = (sizeHint.height() * 72) / self.page.pageSizeF().height()
            image = self.page.renderToImage(xDpi, yDpi)

            # If we ask to render an image that's too large, it will return
            # an empty 1x1 image.  Contrary to what the Poppler docs say,
            # it does not return a null image
            if image.isNull() or image.size() == QSize(1, 1):
                sizeHint /= 2
                continue

            self._qImage = image
            self._qImageSize = sizeHint

        return self._qImage

class InputPDFFile(object):
    def __init__(self, fileName):
        # Make a copy of the file in a temporary directory.  This way we
        # can reference it without worrying about the underlying file
        # changing.
        self.tmpDir = tempfile.TemporaryDirectory(prefix="pdfXplode-inPDF")
        self.tmpFileName = os.path.join(self.tmpDir.name,
                                        os.path.basename(fileName))
        shutil.copyfile(fileName, self.tmpFileName)

        self.doc = Poppler.Document.load(self.tmpFileName)
        self.doc.setRenderHint(Poppler.Document.Antialiasing, True)
        self.doc.setRenderHint(Poppler.Document.TextAntialiasing, True)
        self.doc.setRenderHint(Poppler.Document.TextHinting, True)

    def cleanup(self):
        self.tmpDir.cleanup()
        self.tmpDir = None
        self.tmpFileName = None
        self.pdfReader = None

    def getNumPages(self):
        return self.doc.numPages()

    def getPage(self, pageNumber):
        return InputPDFPage(self, pageNumber)

    def getPyPDF2Reader(self):
        return PyPDF2.PdfFileReader(self.tmpFileName)
