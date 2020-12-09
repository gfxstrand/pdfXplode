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

#include "ScaledSpinBox.h"
#include "Unit.h"

#include <QtWidgets/QPushButton>

class Linked2DSpinBox : public QWidget
{
    Q_OBJECT

public:
    Linked2DSpinBox(QWidget *parent, const QString &xName = "X",
                    const QString &yName = "Y", bool compact = false);
    virtual ~Linked2DSpinBox();

    inline bool linked() { return _link && _link->isChecked(); }
    inline void setLinked(bool linked) { _link->setChecked(linked); }

    inline QSizeF value() { return QSizeF(_xSpin->value(), _ySpin->value()); }
    inline void setValue(const QSizeF &val)
    {
        _xSpin->setValue(val.width());
        _ySpin->setValue(val.height());
    }

    void setBaseValue(const QSizeF &base);
    void setBaseUnit(Unit unit);
    void setDisplayUnit(Unit unit);

    inline void setMaximum(const QSizeF &val)
    {
        _xSpin->setMaximum(val.width());
        _ySpin->setMaximum(val.height());
    }

private slots:
    void linkToggled(bool checked);
    void xChanged(double x);
    void yChanged(double y);

signals:
    void valueChanged(QSizeF val);

private:
    void resetScale();

    QSizeF _base;
    Unit _baseUnit;
    Unit _displayUnit;

    ScaledSpinBox *_xSpin;
    ScaledSpinBox *_ySpin;
    QPushButton *_link;
    bool _updating;
    QIcon _linkIcon;
    QIcon _unlinkIcon;
};
