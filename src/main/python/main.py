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
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
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
    QVBoxLayout,
    QWidget
)
import sys

class DimWidget(QGroupBox):
    def __init__(self, title, xName='X', yName='Y', parent=None):
        super(DimWidget, self).__init__(parent)

        self.setTitle(title)

        self.xLabel = QLabel(xName + ':')
        self.yLabel = QLabel(yName + ':')
        self.xSpin = QDoubleSpinBox()
        self.ySpin = QDoubleSpinBox()

        self.link = QPushButton('Link')
        self.link.setCheckable(True)
        self.link.setChecked(True)

        layout = QGridLayout()
        layout.addWidget(self.xLabel, 0, 0, 2, 1)
        layout.addWidget(self.xSpin, 0, 1, 2, 1)
        layout.addWidget(self.yLabel, 2, 0, 2, 1)
        layout.addWidget(self.ySpin, 2, 1, 2, 1)
        layout.addWidget(QLabel('↰'), 0, 2, 1, 1)
        layout.addWidget(self.link, 1, 2, 2, 1)
        layout.addWidget(QLabel('↲'), 3, 2, 1, 1)
        self.setLayout(layout)

class PreviewWidget(QLabel):
    def __init__(self, parent=None):
        super(PreviewWidget, self).__init__(parent)
        self.path = None
        self.page = 0

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

        # Scale widget
        self.scale = DimWidget('Size', 'X', 'Y')
        formLayout.addWidget(self.scale)

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

    def loadPDF(self, fname):
        self.filname = fname
        self.preview.setPDFPath(fname)

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
