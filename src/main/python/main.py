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

from fbs_runtime.application_context.PyQt5 import ApplicationContext
import pdf2image
import PIL
import PIL.ImageQt
from PyPDF2 import PdfFileReader
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenuBar,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget
)
import sys

class DimWidget(QWidget):
    def __init__(self, xName='X', yName='Y', parent=None):
        super(DimWidget, self).__init__(parent)

        self.x = 0
        self.y = 0
        self.xBase = 1
        self.yBase = 1
        self.xMax = 0
        self.yMax = 0
        self.units = 'percent'
        self.xPointsPerUnit = 1
        self.yPointsPerUnit = 1

        self.xLabel = QLabel(xName + ':')
        self.yLabel = QLabel(yName + ':')
        self.xSpin = QDoubleSpinBox()
        self.ySpin = QDoubleSpinBox()

        self.link = QPushButton('Link')
        self.link.setCheckable(True)
        self.link.setChecked(True)

        self.unitsBox = QComboBox()
        self.unitsBox.setEditable(False)
        self.unitsBox.addItem('inches')
        self.unitsBox.addItem('percent')
        self.unitsBox.addItem('points')
        self.unitsBox.setCurrentText(self.units)
        self.unitsBox.currentTextChanged.connect(self.setUnits)

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.xLabel, 0, 0, 2, 1)
        layout.addWidget(self.xSpin, 0, 1, 2, 1)
        layout.addWidget(self.yLabel, 2, 0, 2, 1)
        layout.addWidget(self.ySpin, 2, 1, 2, 1)
        layout.addWidget(QLabel('↰'), 0, 2, 1, 1)
        layout.addWidget(self.link, 1, 2, 2, 1)
        layout.addWidget(QLabel('↲'), 3, 2, 1, 1)
        layout.addWidget(self.unitsBox, 4, 1, 1, 2)
        self.setLayout(layout)

    def _updateSpinners(self):
        if self.units == 'inches':
            self.xPointsPerUnit = 72
            self.yPointsPerUnit = 72
        elif self.units == 'percent':
            self.xPointsPerUnit = self.xBase / 100
            self.yPointsPerUnit = self.yBase / 100
        elif self.units == 'points':
            self.xPointsPerUnit = 1
            self.yPointsPerUnit = 1

        self.xSpin.setMaximum(self.xMax / self.xPointsPerUnit)
        self.xSpin.setValue(self.x / self.xPointsPerUnit)
        self.xSpin.setSingleStep(1 / self.xPointsPerUnit)
        self.ySpin.setMaximum(self.yMax / self.yPointsPerUnit)
        self.ySpin.setSingleStep(1 / self.yPointsPerUnit)
        self.ySpin.setValue(self.y / self.yPointsPerUnit)

    def setValue(self, x, y):
        self.x = x
        self.y = y
        self._updateSpinners()

    def setMaximum(self, xMax, yMax):
        self.xMax = xMax
        self.yMax = yMax
        self._updateSpinners()

    def setBaseValue(self, xBase, yBase):
        self.xBase = xBase
        self.yBase = yBase
        self._updateSpinners()

    def setUnits(self, units):
        self.units = units
        self._updateSpinners()

class PreviewWidget(QLabel):
    def __init__(self, parent=None):
        super(PreviewWidget, self).__init__(parent)
        self.path = None
        self.page = 1

    def _reload(self):
        images = pdf2image.convert_from_path(self.path, dpi=100,
                                             first_page=self.page,
                                             last_page=self.page)
        self.image = PIL.ImageQt.ImageQt(images[0])
        self.setPixmap(QPixmap.fromImage(self.image))

    def setPDFPath(self, path):
        if self.path != path:
            self.path = path
            self._reload()

    def setPageNumber(self, page):
        if self.page != page:
            self.page = page
            self._reload()

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.pdf = None
        self.pdfFileName = None
        self.pageNumber = 1

        self.openAction = QAction(QIcon.fromTheme('document-open'), '&Open')
        self.openAction.triggered.connect(self.openFileDialog)

        self.quitAction = QAction(QIcon.fromTheme('application-exit'), '&Quit')
        self.quitAction.triggered.connect(self.close)

        self._setupMenus()

        hLayout = QHBoxLayout()

        # Preview widget
        self.preview = PreviewWidget()
        hLayout.addWidget(self.preview)

        # A parent widget to contain all the knobs
        formWidget = QWidget()
        formLayout = QVBoxLayout()
        formWidget.setLayout(formLayout)
        hLayout.addWidget(formWidget)

        # Page number spinner
        self.pageNumSpin = QSpinBox()
        self.pageNumSpin.setMinimum(1)
        self.pageNumSpin.setMaximum(1)
        self.pageNumSpin.setValue(self.pageNumber)
        self.pageNumSpin.valueChanged.connect(self.setPageNumber)
        pageNumBox = QGroupBox()
        pageNumBox.setTitle('Page Number')
        layout = QHBoxLayout()
        layout.addWidget(self.pageNumSpin)
        pageNumBox.setLayout(layout)
        formLayout.addWidget(pageNumBox)

        # Scale widget
        self.scale = DimWidget('X', 'Y')
        # No one should need more than a mile. :-)
        self.scale.setMaximum(72 * 12 * 5280, 72 * 12 * 5280)
        scaleBox = QGroupBox()
        scaleBox.setTitle('Output Size')
        layout = QVBoxLayout()
        layout.addWidget(self.scale)
        scaleBox.setLayout(layout)
        formLayout.addWidget(scaleBox)

        # A dummy padding widget
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        formLayout.addWidget(spacer)

        wid = QWidget()
        wid.setLayout(hLayout)
        self.setCentralWidget(wid)

        self.setWindowTitle('pdfXplode')

    def _setupMenus(self):
        menuBar = self.menuBar()
        fileMenu = menuBar.addMenu('&File')
        fileMenu.addAction(self.openAction)
        fileMenu.addSeparator()
        fileMenu.addAction(self.quitAction)

    def updatePageSize(self):
        box = self.pdf.getPage(self.pageNumber - 1).mediaBox
        self.scale.setBaseValue(box.upperRight[0], box.upperRight[1])
        self.scale.setValue(box.upperRight[0], box.upperRight[1])

    def setPageNumber(self, pageNumber):
        if self.pageNumber != pageNumber:
            self.pageNumber = pageNumber
            self.preview.setPageNumber(pageNumber)
            self.updatePageSize()

    def loadPDF(self, fileName):
        self.pdfFileName = fileName
        self.pdf = PdfFileReader(fileName)
        self.preview.setPDFPath(fileName)
        self.pageNumSpin.setMaximum(self.pdf.getNumPages())
        self.updatePageSize()

    def openFileDialog(self):
        fname = QFileDialog.getOpenFileName(self, 'Open PDF', None, '*.pdf')
        self.loadPDF(fname[0])

if __name__ == '__main__':
    appctxt = ApplicationContext()

    menuBar = QMenuBar();
    openAct = QAction('&Open')
    menuBar.addAction(openAct)

    window = MainWindow()
    window.loadPDF('/home/jason/resume.pdf')
    window.show()
    sys.exit(appctxt.app.exec_())
