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
from inputPDF import InputPDFFile, InputPDFPage
from inputImage import InputImage
import math
from PyQt5.QtCore import (
    pyqtSignal,
    Qt,
    QRectF,
    QThreadPool,
)
from PyQt5.QtGui import QBrush, QIcon, QPen, QPixmap, QTransform
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QGraphicsScene,
    QGraphicsView,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenuBar,
    QProgressDialog,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget
)
import os
from outputPDF import PDFExportOperation, PrintOperation
import sys
import tempfile
from units import *

MILE_IN_POINTS = 72 * 12 * 5280

class UnitsComboBox(QComboBox):
    valueChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super(UnitsComboBox, self).__init__(parent)
        self.setEditable(False)
        self.currentTextChanged.connect(self._parentTextChanged)
        self._updating = False

    def _parentTextChanged(self, text):
        if not self._updating:
            self.valueChanged.emit(text)

    def value(self):
        return self.currentText()

    def setAvailableUnits(self, availableUnits):
        self._updating = True
        old = self.currentText()
        self.clear()
        self.addItems(availableUnits)
        self._updating = False
        self.setCurrentText(old)

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

        self.displayUnit = POINTS
        self.baseUnit = POINTS
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

        if self.linked():
            self._updating = True
            self.ySpin.setValue(x * (self.yBase / self.xBase))
            self._updating = False

        self.valueChanged.emit(x, self.ySpin.value())

    def _yChanged(self, y):
        if self._updating:
            return

        if self.linked():
            self._updating = True
            self.xSpin.setValue(y * (self.xBase / self.yBase))
            self._updating = False

        self.valueChanged.emit(self.xSpin.value(), y)

    def values(self):
        return self.xSpin.value(), self.ySpin.value()

    def setValues(self, x, y):
        if x != self.xSpin.value() or y != self.ySpin.value():
            self._updating = True
            self.xSpin.setValue(x)
            self.ySpin.setValue(y)
            self._updating = False
            self.valueChanged.emit(x, y)

    def setMaximums(self, xMax, yMax):
        self.xSpin.setMaximum(xMax)
        self.ySpin.setMaximum(yMax)

    def _resetScale(self):
        if self.displayUnit == PERCENT:
            self.xSpin.setScale(self.xBase / 100)
            self.ySpin.setScale(self.yBase / 100)
        else:
            scale = getConversionFactor(self.displayUnit, self.baseUnit)
            self.xSpin.setScale(scale)
            self.ySpin.setScale(scale)

    def setBaseValues(self, xBase, yBase):
        if xBase == self.xBase and yBase == self.yBase:
            return

        x = self.xSpin.value()
        y = self.ySpin.value()

        if self.linked() and x and y and xBase and yBase:
            if xBase == self.xBase:
                y = x * yBase / xBase
            elif yBase == self.yBase:
                x = y * xBase / yBase
            elif abs((x / y) - (xBase / yBase)) > 0.0001:
                yScaled = y * xBase / yBase
                x = (x + yScaled) / 2
                y = x * yBase / xBase
            self.setValues(x, y)

        if self.displayUnit == PERCENT:
            self._resetScale()

        self.xBase = xBase
        self.yBase = yBase

    def setBaseUnit(self, unit):
        self.baseUnit = unit
        self._resetScale()

    def setDisplayUnit(self, unit):
        self.displayUnit = unit
        self._resetScale()

    def linked(self):
        return self.link and self.link.isChecked()

    def setLinked(self, linked):
        if self.link:
            return self.link.setChecked(linked)
        else:
            assert not linked

class PreviewWidget(QGraphicsView):
    def __init__(self, parent=None):
        scene = QGraphicsScene()
        super(PreviewWidget, self).__init__(scene, parent)

        self.scene = scene
        self.inputPage = None
        self.outputSize = (0, 0)
        self.cropSize = (0, 0)
        self.cropOrig = (0, 0)
        self.pageSize = (0, 0)
        self.pageMargin = (0, 0)

        self.cropRectItem = None
        self.pageRectItems = []

        backgroundBrush = QBrush(Qt.gray)
        self.scene.setBackgroundBrush(backgroundBrush)

        self.cropPen = QPen()
        self.cropPen.setStyle(Qt.SolidLine)
        self.cropPen.setWidth(1)
        self.cropPen.setBrush(Qt.red)
        self.cropPen.setCapStyle(Qt.RoundCap)
        self.cropPen.setJoinStyle(Qt.RoundJoin)

        self.pagePen = QPen()
        self.pagePen.setStyle(Qt.SolidLine)
        self.pagePen.setWidth(1)
        self.pagePen.setBrush(Qt.gray)
        self.pagePen.setCapStyle(Qt.RoundCap)
        self.pagePen.setJoinStyle(Qt.RoundJoin)

    def _reload(self):
        self.scene.clear()
        self.image = None
        self.cropRectItem = None
        self.pageRectItems = []
        if not self.inputPage:
            return

        self.image = self.inputPage.getQImage(96 / 72)
        self.pixmap = self.scene.addPixmap(QPixmap.fromImage(self.image))
        pageSize = self.inputPage.getSize()
        # Assume it scales the same in both directions
        assert (pageSize[0] * self.image.height() ==
                pageSize[1] * self.image.width())
        self.pixmap.setScale(pageSize[0] / self.image.width())
        self.setSceneRect(0, 0, pageSize[0], pageSize[1])
        self.setTransform(QTransform().scale(96 / 72, 96 / 72))

    def setInputPage(self, page):
        if self.inputPage != page:
            self.inputPage = page
            self._reload()
            self._updateRects()

    def _updateRects(self):
        if self.cropRectItem:
            self.scene.removeItem(self.cropRectItem)
        self.cropRectItem = None

        for r in self.pageRectItems:
            self.scene.removeItem(r)
        self.pageRectItems = []

        printSize = (self.pageSize[0] - 2 * self.pageMargin[0],
                     self.pageSize[1] - 2 * self.pageMargin[1])
        if printSize[0] == 0 or printSize[1] == 0:
            return

        cropRect = QRectF(self.cropOrig[0], self.cropOrig[1],
                          self.cropSize[0], self.cropSize[1])
        self.cropRectItem = self.scene.addRect(cropRect, pen=self.cropPen,
                                               brush=QBrush(Qt.NoBrush))

        numPagesX = math.ceil(self.outputSize[0] / printSize[0])
        numPagesY = math.ceil(self.outputSize[1] / printSize[1])

        if self.outputSize[0] == 0 or self.outputSize[1] == 0:
            return

        pageRectSize = (printSize[0] * self.cropSize[0] / self.outputSize[0],
                        printSize[1] * self.cropSize[1] / self.outputSize[1])

        for y in range(numPagesY):
            for x in range(numPagesX):
                pageRect = QRectF(self.cropOrig[0] + x * pageRectSize[0],
                                  self.cropOrig[1] + y * pageRectSize[1],
                                  pageRectSize[0],
                                  pageRectSize[1])
                rectItem = self.scene.addRect(pageRect, pen=self.pagePen,
                                              brush=QBrush(Qt.NoBrush))
                self.pageRectItems.append(rectItem)

    def setCropOrig(self, x, y):
        self.cropOrig = (x, y)
        self._updateRects()

    def setCropSize(self, width, height):
        self.cropSize = (width, height)
        self._updateRects()

    def setOutputSize(self, width, height):
        self.outputSize = (width, height)
        self._updateRects()

    def setPageSize(self, width, height):
        self.pageSize = (width, height)
        self._updateRects()

    def setPageMargin(self, width, height):
        self.pageMargin = (width, height)
        self._updateRects()

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.inputPDF = None
        self.inputPage = None
        self.inputPageNumber = 0

        self.openAction = QAction(QIcon.fromTheme('document-open'), '&Open')
        self.openAction.triggered.connect(self.openFileDialog)

        self.exportAction = QAction(QIcon.fromTheme('document-save'),
                                    '&Save PDF')
        self.exportAction.triggered.connect(self.exportFileDialog)

        self.exportAction = QAction(QIcon.fromTheme('document-print'),
                                    '&Print')
        self.exportAction.triggered.connect(self.printDialog)

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
        self.pageNumSpin.setValue(self.inputPageNumber)
        self.pageNumSpin.valueChanged.connect(self.setPageNumber)
        pageNumBox = QGroupBox()
        pageNumBox.setTitle('Page Number')
        layout = QHBoxLayout()
        layout.addWidget(self.pageNumSpin)
        pageNumBox.setLayout(layout)
        formLayout.addWidget(pageNumBox)

        # Scale widget
        self.cropOrig = DimWidget('X', 'Y')
        self.cropOrig.setLinked(False)
        self.cropOrig.valueChanged.connect(self.preview.setCropOrig)
        self.cropDim = DimWidget('Width', 'Height')
        self.cropDim.setLinked(False)
        self.cropDim.valueChanged.connect(self.preview.setCropSize)
        self.cropUnits = UnitsComboBox()
        self.cropUnits.valueChanged.connect(self.cropOrig.setDisplayUnit)
        self.cropUnits.valueChanged.connect(self.cropDim.setDisplayUnit)
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
        self.cropDim.valueChanged.connect(self.scale.setBaseValues)
        self.preview.setOutputSize(*self.scale.values())
        self.scale.valueChanged.connect(self.preview.setOutputSize)
        self.scaleUnits = UnitsComboBox()
        self.scaleUnits.valueChanged.connect(self.scale.setDisplayUnit)
        scaleBox = QGroupBox()
        scaleBox.setTitle('Output Size')
        layout = QVBoxLayout()
        layout.addWidget(self.scale)
        layout.addWidget(self.scaleUnits)
        scaleBox.setLayout(layout)
        formLayout.addWidget(scaleBox)

        # Output page size and margin
        self.outPageSize = DimWidget(compact=True)
        self.outPageSize.setBaseUnit(POINTS)
        self.outPageSize.setMaximums(MILE_IN_POINTS, MILE_IN_POINTS)
        self.outPageSize.setValues(8.5 * 72, 11 * 72)
        self.preview.setPageSize(*self.outPageSize.values())
        self.outPageSize.valueChanged.connect(self.preview.setPageSize)
        self.outPageMargin = DimWidget(compact=True)
        self.outPageMargin.setBaseUnit(POINTS)
        self.outPageMargin.setMaximums(MILE_IN_POINTS, MILE_IN_POINTS)
        self.outPageMargin.setValues(0.5 * 72, 0.5 * 72)
        self.preview.setPageMargin(*self.outPageMargin.values())
        self.outPageMargin.valueChanged.connect(self.preview.setPageMargin)
        self.outPageUnits = UnitsComboBox()
        self.outPageUnits.setAvailableUnits([POINTS, INCHES])
        self.outPageSize.setDisplayUnit(self.outPageUnits.value())
        self.outPageUnits.valueChanged.connect(self.outPageSize.setDisplayUnit)
        self.outPageMargin.setDisplayUnit(self.outPageUnits.value())
        self.outPageUnits.valueChanged.connect(self.outPageMargin.setDisplayUnit)
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

        self.registrationMarks = QCheckBox('Registration Marks')
        self.registrationMarks.setChecked(True)
        formLayout.addWidget(self.registrationMarks)

        self.overDraw = QCheckBox('Over-draw into margin')
        self.overDraw.setChecked(False)
        formLayout.addWidget(self.overDraw)

        self.saveButton = QPushButton('Save PDF')
        self.saveButton.setIcon(QIcon.fromTheme('document-save'))
        self.saveButton.clicked.connect(self.exportFileDialog)
        formLayout.addWidget(self.saveButton)

        self.saveButton = QPushButton('Print')
        self.saveButton.setIcon(QIcon.fromTheme('document-print'))
        self.saveButton.clicked.connect(self.printDialog)
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
        if self.inputPage is None:
            return

        size = self.inputPage.getSize()
        self.cropUnits.setAvailableUnits(self.inputPage.getAllowedUnits())
        self.cropOrig.setMaximums(*size)
        self.cropOrig.setBaseValues(*size)
        self.cropOrig.setValues(0, 0)
        self.cropOrig.setBaseUnit(self.inputPage.getNativeUnit())
        self.cropOrig.setDisplayUnit(self.cropUnits.value())
        self.cropDim.setMaximums(*size)
        self.cropDim.setBaseValues(*size)
        self.cropDim.setValues(*size)
        self.cropDim.setBaseUnit(self.inputPage.getNativeUnit())
        self.cropDim.setDisplayUnit(self.cropUnits.value())
        if self.inputPage.getNativeUnit() == POINTS:
            self.scaleUnits.setAvailableUnits([PERCENT, POINTS, INCHES])
        else:
            self.scaleUnits.setAvailableUnits([POINTS, INCHES])
        self.scale.setBaseValues(*size)
        self.scale.setValues(*size)
        self.scale.setDisplayUnit(self.scaleUnits.value())

    def setPageNumber(self, pageNumber):
        if self.inputPDF is None:
            return # Only PDFs have page numbers

        if self.inputPageNumber != pageNumber or self.inputPage is None:
            if self.inputPage is not None:
                self.inputPage.cleanup()
            self.inputPageNumber = pageNumber
            self.inputPage = self.inputPDF.getPage(pageNumber)
            self.preview.setInputPage(self.inputPage)
            self._updatePageSize()

    def loadPDF(self, fileName):
        if self.inputPDF:
            self.inputPDF.cleanup()
        self.inputPDF = InputPDFFile(fileName)
        self.inputPage = None
        self.pageNumSpin.setDisabled(False)
        self.pageNumSpin.setMaximum(self.inputPDF.getNumPages())
        self.setPageNumber(self.pageNumSpin.value())

    def loadImage(self, fileName):
        if self.inputPDF:
            self.inputPDF.cleanup()
        self.inputPDF = None
        self.inputPage = InputImage(fileName)
        self.pageNumSpin.setDisabled(True)
        self.preview.setInputPage(self.inputPage)
        self._updatePageSize()

    def exportPDF(self, fileName):
        progress = QProgressDialog(self)
        progress.setLabelText("Saving exploded PDF...")
        progress.setCancelButtonText("Cancel")
        progress.setWindowModality(Qt.WindowModal)

        export = PDFExportOperation(
            fileName,
            self.inputPage,
            self.cropOrig.values(),
            self.cropDim.values(),
            self.scale.values(),
            self.outPageSize.values(),
            self.outPageMargin.values(),
            trim=not self.overDraw.isChecked(),
            registrationMarks=self.registrationMarks.isChecked(),
            progress=progress)

        progress.show()

        QThreadPool.globalInstance().start(export)

    def openFileDialog(self):
        filters = 'PDF files (*.pdf);;Images (*.png *.jpg)'
        fname = QFileDialog.getOpenFileName(self, 'Open input file',
                                            filter=filters)
        if not fname or not fname[0]:
            return # Canceled

        ext = os.path.splitext(fname[0])[1].lower()
        if ext == '.pdf':
            self.loadPDF(fname[0])
        elif ext in ('.png', '.jpg'):
            self.loadImage(fname[0])
        else:
            raise RuntimeError("Unknown file extension")

    def exportFileDialog(self):
        fname = QFileDialog.getSaveFileName(self, 'Export PDF', filter='*.pdf')
        if fname and fname[0]:
            self.exportPDF(fname[0])

    def printDialog(self):
        printOp = PrintOperation(
            self.inputPage,
            self.cropOrig.values(),
            self.cropDim.values(),
            self.scale.values(),
            self.outPageSize.values(),
            self.outPageMargin.values(),
            trim=not self.overDraw.isChecked(),
            registrationMarks=self.registrationMarks.isChecked(),
            progress=None)

        printDialog = QPrintDialog(printOp.printer, self)
        if printDialog.exec_() == QDialog.Accepted:
            printOp.run()

if __name__ == '__main__':
    appctxt = ApplicationContext()

    menuBar = QMenuBar();
    openAct = QAction('&Open')
    menuBar.addAction(openAct)

    window = MainWindow()
    window.show()
    sys.exit(appctxt.app.exec_())
