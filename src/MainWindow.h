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

#pragma once

#include "CropWidget.h"
#include "InputPage.h"
#include "Linked2DSpinBox.h"
#include "UnitsComboBox.h"

#include <QtWidgets/QAction>
#include <QtWidgets/QCheckBox>
#include <QtWidgets/QMainWindow>
#include <QtWidgets/QSpinBox>

#include <memory>

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    MainWindow();
    virtual ~MainWindow();

    void loadImage(const QString &fileName);

private slots:
    void pageNumberChanged(int pageNumber);
    void openFileDialog();
    void openPrintDialog();

private:
    void updatePageSize();

    // Actions
    QAction *_openAction;
    QAction *_printAction;
    QAction *_quitAction;

    std::unique_ptr<InputPage> _inPage;

    CropWidget *_crop;
    QSpinBox *_pageNumber;
    Linked2DSpinBox *_cropOrig;
    Linked2DSpinBox *_cropSize;
    UnitsComboBox *_cropUnits;

    Linked2DSpinBox *_outSize;
    UnitsComboBox *_outUnits;

    QCheckBox *_overDraw;
    QCheckBox *_registrationMarks;
};
