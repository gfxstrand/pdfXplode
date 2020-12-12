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

import io
import os
import poppler
import PyPDF2
from PyQt5.QtCore import QSize, QSizeF
from PyQt5.QtGui import QImage
import shutil
import tempfile
import units

POPPLER_TO_QT_FORMAT = {
    poppler.ImageFormat.invalid: QImage.Format_Invalid,
    poppler.ImageFormat.argb32: QImage.Format_ARGB32,
    poppler.ImageFormat.bgr24: QImage.Format_BGR888,
    poppler.ImageFormat.gray8: QImage.Format_Grayscale8,
    poppler.ImageFormat.mono: QImage.Format_Mono,
    poppler.ImageFormat.rgb24: QImage.Format_RGB888,
}

class InputPDFPage(object):
    def __init__(self, pdfFile, pageNumber):
        self.pdfFile = pdfFile
        self.pageNumber = pageNumber
        self.page = pdfFile.doc.create_page(pageNumber - 1)
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

    def getSizeF(self):
        rect = self.page.page_rect(poppler.PageBox.media_box)
        assert rect.x == 0 and rect.y == 0
        return QSizeF(rect.width, rect.height)

    def getSize(self):
        return self.getSizeF().toSize()

    def getQImage(self, sizeHint=None):
        if sizeHint == None:
            sizeHint = self.page.pageSize()

        assert sizeHint.width() > 1 and sizeHint.height() > 1

        if self._qImageSize != sizeHint:
            self._qImage = None

        renderer = poppler.PageRenderer()
        renderer.set_render_hint(poppler.RenderHint.antialiasing, True)
        renderer.set_render_hint(poppler.RenderHint.text_antialiasing, True)
        renderer.set_render_hint(poppler.RenderHint.text_hinting, True)

        while self._qImage is None:
            xDpi = (sizeHint.width() * 72) / self.getSizeF().width()
            yDpi = (sizeHint.height() * 72) / self.getSizeF().height()
            image = renderer.render_page(self.page, xDpi, yDpi)

            qImage = QImage(image.data, image.width, image.height,
                            image.bytes_per_row,
                            POPPLER_TO_QT_FORMAT[image.format])

            # If we ask Qt to import an image that's too large for it to
            # handle, it will return an empty 1x1 image rather than a null
            # image.
            if qImage.isNull() or qImage.size() == QSize(1, 1):
                sizeHint /= 2
                continue

            self._qImage = QImage(image.data, image.width, image.height,
                                  image.bytes_per_row,
                                  POPPLER_TO_QT_FORMAT[image.format])
            self._qImageSize = sizeHint

        return self._qImage

class InputPDFFile(object):
    def __init__(self, fileName):
        # Read the entire file because we'll need to open it with multiple
        # different PDF libraries
        with open(fileName, 'rb') as f:
            self.bytes = f.read()

        self.doc = poppler.document.load_from_data(self.bytes)

    def cleanup(self):
        self.tmpDir.cleanup()
        self.tmpDir = None
        self.tmpFileName = None
        self.pdfReader = None

    def getNumPages(self):
        return self.doc.pages

    def getPage(self, pageNumber):
        return InputPDFPage(self, pageNumber)

    def getPyPDF2Reader(self):
        return PyPDF2.PdfFileReader(io.BytesIO(self.bytes))
