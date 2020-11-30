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
import math
import pdf2image
import PIL
import PIL.ImageQt
from PyPDF2 import PdfFileReader, PdfFileWriter
from PyQt5.QtCore import pyqtSignal, QRunnable
from PyQt5.QtGui import QIcon, QPixmap, QTransform
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

MILE_IN_POINTS = 72 * 12 * 5280

def pointsPerUnit(unit, base):
    if unit == 'inches':
        return 72
    elif unit == 'percent':
        return base / 100
    elif unit == 'points':
        return 1

class UnitsComboBox(QComboBox):
    valueChanged = pyqtSignal(str)

    def __init__(self, parent=None, percent=True):
        super(UnitsComboBox, self).__init__(parent)

        self.setEditable(False)
        self.addItem('inches')
        if percent:
            self.addItem('percent')
        self.addItem('points')
        self.currentTextChanged.connect(self.valueChanged)

class ScaledSpinBox(QWidget):
    valueChanged = pyqtSignal(float)

    def __init__(self, parent=None):
        super(ScaledSpinBox, self).__init__(parent)

        self._raw = QDoubleSpinBox()
        self._raw.valueChanged.connect(self._rawValueChanged)
        self._updating = False
        self._scale = 1

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._raw)
        self.setLayout(layout)

    def _rawValueChanged(self, rawValue):
        if not self._updating:
            self.valueChanged.emit(rawValue * self._scale)

    def minimum(self):
        return self._raw.minimum() * self._scale

    def setMinimum(self, value):
        self._raw.setMinimum(value / self._scale)

    def maximum(self):
        return self._raw.maximum() * self._scale

    def setMaximum(self, value):
        self._raw.setMaximum(value / self._scale)

    def value(self):
        return self._raw.value() * self._scale

    def setValue(self, value):
        self._raw.setValue(value / self._scale)

    def singleStep(self):
        return self._raw.singleStep() * self._scale

    def setSingleStep(self, step):
        self._raw.setSingleStep(step / self._scale)

    def scale(self):
        return self._scale

    def setScale(self, scale):
        mini = self.minimum()
        maxi = self.maximum()
        step = self.singleStep()
        value = self.value()
        self.updating = True
        self._scale = scale
        self.setMinimum(mini)
        self.setMaximum(maxi)
        self.setSingleStep(step)
        self.setValue(value)
        self.updating = False

class DimWidget(QWidget):
    valueChanged = pyqtSignal(float, float)

    def __init__(self, xName='X', yName='Y', compact=False, parent=None):
        super(DimWidget, self).__init__(parent)

        self._updating = False

        self.xBase = 1
        self.yBase = 1

        self.xSpin = ScaledSpinBox()
        self.xSpin.valueChanged.connect(self._xChanged)
        self.ySpin = ScaledSpinBox()
        self.ySpin.valueChanged.connect(self._yChanged)
        self.link = None

        if compact:
            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.xSpin)
            layout.addWidget(QLabel('x'))
            layout.addWidget(self.ySpin)
            self.setLayout(layout)
        else:
            self.link = QPushButton('Link')
            self.link.setCheckable(True)
            self.link.setChecked(True)

            layout = QGridLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(QLabel(xName + ':'), 0, 0, 2, 1)
            layout.addWidget(self.xSpin, 0, 1, 2, 1)
            layout.addWidget(QLabel(yName + ':'), 2, 0, 2, 1)
            layout.addWidget(self.ySpin, 2, 1, 2, 1)
            layout.addWidget(QLabel('↰'), 0, 2, 1, 1)
            layout.addWidget(self.link, 1, 2, 2, 1)
            layout.addWidget(QLabel('↲'), 3, 2, 1, 1)
            self.setLayout(layout)

    def _xChanged(self, x):
        if self._updating:
            return

        if self.link and self.link.isChecked():
            self._updating = True
            self.ySpin.setValue(x * (self.yBase / self.xBase))
            self._updating = False

        self.valueChanged.emit(x, self.ySpin.value())

    def _yChanged(self, y):
        if self._updating:
            return

        if self.link and self.link.isChecked():
            self._updating = True
            self.xSpin.setValue(y * (self.xBase / self.yBase))
            self._updating = False

        self.valueChanged.emit(self.xSpin.value(), y)

    def values(self):
        return self.xSpin.value(), self.ySpin.value()

    def setValues(self, x, y):
        self.xSpin.setValue(x)
        self.ySpin.setValue(y)

    def setMaximums(self, xMax, yMax):
        self.xSpin.setMaximum(xMax)
        self.ySpin.setMaximum(yMax)

    def setBaseValues(self, xBase, yBase):
        self.xBase = xBase
        self.yBase = yBase

    def setUnits(self, unit):
        self.xSpin.setScale(pointsPerUnit(unit, self.xBase))
        self.ySpin.setScale(pointsPerUnit(unit, self.yBase))

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

class PDFExportOperation(QRunnable):
    def __init__(self, inPage, outFileName, cropOrig, cropSize,
                 outSize, pageSize, pageMargin):
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
        self.globalXform.translate(-cropOrig[0], -cropOrig[1])
        self.globalXform.scale(outSize[0] / cropSize[0],
                               outSize[1] / cropSize[1])

        self.numPagesX = math.ceil(outSize[0] / self.printableWidth)
        self.numPagesY = math.ceil(outSize[1] / self.printableHeight)

    def run(self):
        outPDF = PdfFileWriter()

        for y in range(self.numPagesY):
            for x in range(self.numPagesX):
                xt = x * self.printableWidth
                yt = y * self.printableHeight

                # PDF coordinates start at the bottom-left but most people
                # think top-down so flip the Y transform
                yt = self.outSize[1] - yt - self.printableHeight

                pageXform = QTransform(self.globalXform).translate(-xt, -yt)
                pageXform.translate(self.pageMargin[0], self.pageMargin[1])
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
                page.mergeTransformedPage(self.inPage, ctm)

        with open(self.outFileName, 'wb') as f:
            outPDF.write(f)

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.pdf = None
        self.pdfFileName = None
        self.pageNumber = 1

        self.openAction = QAction(QIcon.fromTheme('document-open'), '&Open')
        self.openAction.triggered.connect(self.openFileDialog)

        self.exportAction = QAction(QIcon.fromTheme('document-save'), '&Export')
        self.exportAction.triggered.connect(self.exportFileDialog)

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
        self.cropOrig = DimWidget('X', 'Y')
        self.cropDim = DimWidget('Width', 'Height')
        self.cropUnits = UnitsComboBox()
        self.cropUnits.valueChanged.connect(self.cropOrig.setUnits)
        self.cropUnits.valueChanged.connect(self.cropDim.setUnits)
        cropBox = QGroupBox()
        cropBox.setTitle('Input Crop')
        layout = QVBoxLayout()
        layout.addWidget(self.cropOrig)
        layout.addWidget(self.cropDim)
        layout.addWidget(self.cropUnits)
        cropBox.setLayout(layout)
        formLayout.addWidget(cropBox)

        # Scale widget
        self.scale = DimWidget('X', 'Y')
        self.scale.setMaximums(MILE_IN_POINTS, MILE_IN_POINTS)
        self.scaleUnits = UnitsComboBox()
        self.scaleUnits.valueChanged.connect(self.scale.setUnits)
        scaleBox = QGroupBox()
        scaleBox.setTitle('Output Size')
        layout = QVBoxLayout()
        layout.addWidget(self.scale)
        layout.addWidget(self.scaleUnits)
        scaleBox.setLayout(layout)
        formLayout.addWidget(scaleBox)

        # Output page size and margin
        self.outPageSize = DimWidget(compact=True)
        self.outPageSize.setMaximums(MILE_IN_POINTS, MILE_IN_POINTS)
        self.outPageSize.setValues(8.5 * 72, 11 * 72)
        self.outPageMargin = DimWidget(compact=True)
        self.outPageMargin.setMaximums(MILE_IN_POINTS, MILE_IN_POINTS)
        self.outPageMargin.setValues(0.5 * 72, 0.5 * 72)
        self.outPageUnits = UnitsComboBox(percent=False)
        self.outPageSize.setUnits(self.outPageUnits.currentText())
        self.outPageUnits.valueChanged.connect(self.outPageSize.setUnits)
        self.outPageMargin.setUnits(self.outPageUnits.currentText())
        self.outPageUnits.valueChanged.connect(self.outPageMargin.setUnits)
        outPageBox = QGroupBox()
        outPageBox.setTitle('Output Page')
        layout = QVBoxLayout()
        layout.addWidget(QLabel('Size:'))
        layout.addWidget(self.outPageSize)
        layout.addWidget(QLabel('Margin:'))
        layout.addWidget(self.outPageMargin)
        layout.addWidget(self.outPageUnits)
        outPageBox.setLayout(layout)
        formLayout.addWidget(outPageBox)

        self.saveButton = QPushButton('Export')
        self.saveButton.setIcon(QIcon.fromTheme('document-save'))
        self.saveButton.clicked.connect(self.exportFileDialog)
        formLayout.addWidget(self.saveButton)

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

    def _updatePageSize(self):
        box = self.pdf.getPage(self.pageNumber - 1).mediaBox
        self.cropOrig.setMaximums(box.upperRight[0], box.upperRight[1])
        self.cropOrig.setBaseValues(box.upperRight[0], box.upperRight[1])
        self.cropOrig.setValues(0, 0)
        self.cropOrig.setUnits(self.cropUnits.currentText())
        self.cropDim.setMaximums(box.upperRight[0], box.upperRight[1])
        self.cropDim.setBaseValues(box.upperRight[0], box.upperRight[1])
        self.cropDim.setValues(box.upperRight[0], box.upperRight[1])
        self.cropDim.setUnits(self.cropUnits.currentText())
        self.scale.setBaseValues(box.upperRight[0], box.upperRight[1])
        self.scale.setValues(box.upperRight[0], box.upperRight[1])
        self.scale.setUnits(self.cropUnits.currentText())

    def setPageNumber(self, pageNumber):
        if self.pageNumber != pageNumber:
            self.pageNumber = pageNumber
            self.preview.setPageNumber(pageNumber)
            self._updatePageSize()

    def loadPDF(self, fileName):
        self.pdfFileName = fileName
        self.pdf = PdfFileReader(fileName)
        self.preview.setPDFPath(fileName)
        self.pageNumSpin.setMaximum(self.pdf.getNumPages())
        self._updatePageSize()

    def exportPDF(self, fileName):
        export = PDFExportOperation(
            self.pdf.getPage(self.pageNumber - 1),
            fileName,
            self.cropOrig.values(),
            self.cropDim.values(),
            self.scale.values(),
            self.outPageSize.values(),
            self.outPageMargin.values())
        export.run()

    def openFileDialog(self):
        fname = QFileDialog.getOpenFileName(self, 'Open PDF', filter='*.pdf')
        if fname and fname[0]:
            self.loadPDF(fname[0])

    def exportFileDialog(self):
        fname = QFileDialog.getSaveFileName(self, 'Export PDF', filter='*.pdf')
        if fname and fname[0]:
            self.exportPDF(fname[0])


if __name__ == '__main__':
    appctxt = ApplicationContext()

    menuBar = QMenuBar();
    openAct = QAction('&Open')
    menuBar.addAction(openAct)

    window = MainWindow()
    window.loadPDF('/home/jason/resume.pdf')
    window.show()
    sys.exit(appctxt.app.exec_())
