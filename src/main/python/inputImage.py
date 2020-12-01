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
from PyQt5.QtGui import QImage
import shutil
import tempfile
import units

class InputImage(object):
    def __init__(self, fileName):
        # Make a copy of the file in a temporary directory.  This way we
        # can reference it without worrying about the underlying file
        # changing.
        self.tmpDir = tempfile.TemporaryDirectory(prefix="pdfXplode-inImage")
        self.tmpFileName = os.path.join(self.tmpDir.name,
                                        os.path.basename(fileName))
        shutil.copyfile(fileName, self.tmpFileName)

        self._qImage = None

    def cleanup(self):
        self._qImage = None

    def getAllowedUnits(self):
        return [units.PIXELS]

    def getNativeUnit(self):
        return units.PIXELS

    def getSize(self):
        size = self.getQImage().size()
        return (size.width(), size.height())

    def getQImage(self, preferredScale=1.0):
        if self._qImage is None:
            self._qImage = QImage()
            self._qImage.load(self.tmpFileName)

        return self._qImage