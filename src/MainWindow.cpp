/* Copyright © 2020 Jason Ekstrand
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

#include "MainWindow.h"

#include "InputImage.h"
#include "print.h"

#include <QtCore/QSettings>
#include <QtPrintSupport/QPrintPreviewDialog>
#include <QtWidgets/QFileDialog>
#include <QtWidgets/QGroupBox>
#include <QtWidgets/QHBoxLayout>
#include <QtWidgets/QMenuBar>
#include <QtWidgets/QPushButton>
#include <QtWidgets/QVBoxLayout>

#define MILE_IN_POINTS (72 * 12 * 5280)

MainWindow::MainWindow() :
    QMainWindow(nullptr)
{
    _openAction = new QAction(QIcon::fromTheme("document-open"),
                              "&Open", this);
    connect(_openAction, &QAction::triggered,
            this, &MainWindow::openFileDialog);

    _printAction = new QAction(QIcon::fromTheme("document-print"),
                               "&Print", this);
    connect(_printAction, &QAction::triggered,
            this, &MainWindow::openPrintDialog);

    _quitAction = new QAction(QIcon::fromTheme("application-exit"),
                              "&Quit", this);
    connect(_quitAction, &QAction::triggered, this, &MainWindow::close);

    auto centralWidget = new QWidget(this);
    setCentralWidget(centralWidget);
    // Primary layout
    auto hLayout = new QHBoxLayout(centralWidget);

    // Set up the menu bar
    auto fileMenu = menuBar()->addMenu("&File");
    fileMenu->addAction(_openAction);
    fileMenu->addAction(_printAction);
    fileMenu->addSeparator();
    fileMenu->addAction(_quitAction);

    // Preview and crop widget
    _crop = new CropWidget(this);
    hLayout->addWidget(_crop);

    // A parent widget to contain all the knobs
    auto formWidget = new QWidget(this);
    auto formLayout = new QVBoxLayout(formWidget);
    hLayout->addWidget(formWidget);

    // Page number spinner
    _pageNumber = new QSpinBox(this);
    _pageNumber->setMinimum(1);
    _pageNumber->setMaximum(1);
    connect(_pageNumber, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &MainWindow::pageNumberChanged);
    // Wrap it in a box
    {
        auto pageNumBox = new QGroupBox("Page Number", this);
        formLayout->addWidget(pageNumBox);

        auto layout = new QHBoxLayout(pageNumBox);
        layout->addWidget(_pageNumber);
    }

    // Crop size and origin widgets
    _cropOrig = new Linked2DSpinBox(this, "X", "Y");
    _cropOrig->setLinked(false);
    connect(_cropOrig, &Linked2DSpinBox::valueChanged,
            _crop, [=](QSizeF val){ _crop->setCropOrig(QPoint(val.width(), val.height())); });
    _cropSize = new Linked2DSpinBox(this, "Width", "Height");
    _cropSize->setLinked(false);
    connect(_cropSize, &Linked2DSpinBox::valueChanged,
            _crop, [=](QSizeF val){ _crop->setCropSize(val.toSize()); });
    _cropUnits = new UnitsComboBox(this);
    connect(_cropUnits, &UnitsComboBox::valueChanged,
            _cropOrig, &Linked2DSpinBox::setDisplayUnit);
    connect(_cropUnits, &UnitsComboBox::valueChanged,
            _cropSize, &Linked2DSpinBox::setDisplayUnit);
    // Wrap it in a box
    {
        auto cropBox = new QGroupBox("Input Crop", this);
        formLayout->addWidget(cropBox);

        auto layout = new QVBoxLayout(cropBox);
        layout->addWidget(_cropOrig);
        layout->addWidget(_cropSize);
        layout->addWidget(_cropUnits);
    }

    _outSize = new Linked2DSpinBox(this, "Width", "Height");
    _outSize->setMaximum(QSizeF(MILE_IN_POINTS, MILE_IN_POINTS));
    connect(_cropSize, &Linked2DSpinBox::valueChanged,
            _outSize, &Linked2DSpinBox::setBaseValue);
    _outUnits = new UnitsComboBox(this);
    connect(_outUnits, &UnitsComboBox::valueChanged,
            _outSize, &Linked2DSpinBox::setDisplayUnit);
    // Wrap it in a box
    {
        auto outBox = new QGroupBox("Output Size", this);
        formLayout->addWidget(outBox);

        auto layout = new QVBoxLayout(outBox);
        layout->addWidget(_outSize);
        layout->addWidget(_outUnits);
    }

    _registrationMarks = new QCheckBox("Registration Marks", this);
    _registrationMarks->setChecked(true);
    formLayout->addWidget(_registrationMarks);

    _overDraw = new QCheckBox("Over-draw into margin", this);
    _overDraw->setChecked(false);
    formLayout->addWidget(_overDraw);

    auto printButton = new QPushButton("Print", this);
    printButton->setIcon(QIcon::fromTheme("document-print"));
    connect(printButton, &QPushButton::clicked,
            this, &MainWindow::openPrintDialog);
    formLayout->addWidget(printButton);
}

MainWindow::~MainWindow()
{ }

void
MainWindow::loadImage(const QString &fileName)
{
    std::unique_ptr<InputImage> newImage(new InputImage(fileName));
    _pageNumber->setDisabled(true);
    _crop->setInputPage(newImage.get());
    _inPage.reset(newImage.release());
    updatePageSize();
}

void
MainWindow::pageNumberChanged(int pageNumber)
{
    if (pageNumber != 0)
        throw std::runtime_error("Unimplemented");
}

void
MainWindow::openFileDialog()
{
    QString filters = "All supported files (*.png *.jpg)";
    filters += ";;Images (*.png *.jpg)";
    QString fileName = QFileDialog::getOpenFileName(this, "Open input file",
                                                    "", filters);
    if (fileName.endsWith(".png", Qt::CaseInsensitive) ||
        fileName.endsWith(".jpg", Qt::CaseInsensitive))
        loadImage(fileName);
    else
        throw std::runtime_error("Unknown file extension");
}

void
MainWindow::openPrintDialog()
{
    QSettings settings;

    QPrinter printer;
    printer.setColorMode(QPrinter::Color);

    QPageLayout defaultPageLayout(QPageSize(QPageSize::Letter),
                                  QPageLayout::Portrait,
                                  QMarginsF(0.5, 0.5, 0.5, 0.5),
                                  QPageLayout::Inch);
    QVariant pageLayoutVariant =
        settings.value("output/page-layout",
                       QVariant::fromValue(defaultPageLayout));
    QPageLayout pageLayout = pageLayoutVariant.value<QPageLayout>();
    printer.setPageLayout(pageLayout);

    QRect cropRect = QRect(QPoint(_cropOrig->value().width(),
                                  _cropOrig->value().height()),
                           _cropSize->value().toSize());
    QSize outSize = _outSize->value().toSize();
    bool trim = !_overDraw->isChecked();
    bool registrationMarks = _registrationMarks->isChecked();

    QPrintPreviewDialog preview(&printer, this);
    connect(&preview, &QPrintPreviewDialog::paintRequested,
            this, [=](QPrinter *printer){
                printInputPage(printer, _inPage.get(), cropRect, outSize,
                               trim, registrationMarks);
            });

    if (preview.exec() == QDialog::Accepted) {
        settings.setValue("output/page-layout",
                          QVariant::fromValue(printer.pageLayout()));
    }
}

void
MainWindow::updatePageSize()
{
    if (!_inPage)
        return;

    auto size = _inPage->sizeInNativeUnit();
    _cropUnits->setAvailableUnits(_inPage->allowedUnits());
    _cropOrig->setMaximum(size);
    _cropOrig->setBaseValue(size);
    _cropOrig->setValue(QSizeF(0, 0));
    _cropOrig->setBaseUnit(_inPage->nativeUnit());
    _cropOrig->setDisplayUnit(_cropUnits->value());
    _cropSize->setMaximum(size);
    _cropSize->setBaseValue(size);
    _cropSize->setValue(size);
    _cropSize->setBaseUnit(_inPage->nativeUnit());
    _cropSize->setDisplayUnit(_cropUnits->value());

    QList<Unit> outUnitList;
    if (_inPage->nativeUnit() == UNIT_POINTS)
        outUnitList.push_back(UNIT_PERCENT);
    outUnitList.push_back(UNIT_INCHES);
    outUnitList.push_back(UNIT_POINTS);
    _outUnits->setAvailableUnits(outUnitList);
    _outSize->setBaseValue(size);
    _outSize->setValue(size);
    _outSize->setDisplayUnit(_outUnits->value());
}
