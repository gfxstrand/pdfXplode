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

#include "Linked2DSpinBox.h"

#include <QtWidgets/QHBoxLayout>
#include <QtWidgets/QLabel>

Linked2DSpinBox::Linked2DSpinBox(QWidget *parent, const QString &xName,
                                 const QString &yName, bool compact) :
    QWidget(parent),
    _base(1, 1),
    _baseUnit(UNIT_NONE),
    _displayUnit(UNIT_NONE),
    _updating(false)
{
    _base = QSizeF(1, 1);

    _xSpin = new ScaledSpinBox(this);
    connect(_xSpin, &ScaledSpinBox::valueChanged,
            this, &Linked2DSpinBox::xChanged);

    _ySpin = new ScaledSpinBox(this);
    connect(_ySpin, &ScaledSpinBox::valueChanged,
            this, &Linked2DSpinBox::yChanged);

    if (compact) {
        _link = nullptr;
        auto layout = new QHBoxLayout(this);
        layout->setContentsMargins(0, 0, 0, 0);
        layout->addWidget(_xSpin);
        layout->addWidget(new QLabel("x", this));
        layout->addWidget(_ySpin);
        setLayout(layout);
    } else {
        _linkIcon = QIcon(":/icons/spin-link.svg");
        _unlinkIcon = QIcon(":/icons/spin-unlink.svg");
        _link = new QPushButton(this);
        _link->setIcon(_linkIcon);
        _link->setCheckable(true);
        _link->setChecked(true);
        _link->setFixedSize(32, 40);
        connect(_link, &QPushButton::toggled,
                this, &Linked2DSpinBox::linkToggled);

        auto layout = new QGridLayout(this);
        layout->setContentsMargins(0, 0, 0, 0);
        layout->addWidget(new QLabel(xName + ':', this), 0, 0, 2, 1);
        layout->addWidget(_xSpin, 0, 1, 2, 1);
        layout->addWidget(new QLabel(yName + ':', this), 2, 0, 2, 1);
        layout->addWidget(_ySpin, 2, 1, 2, 1);
        layout->addWidget(new QLabel("↰", this), 0, 2, 1, 1);
        layout->addWidget(_link, 1, 2, 2, 1);
        layout->addWidget(new QLabel("↲", this), 3, 2, 1, 1);
        setLayout(layout);
    }
}

Linked2DSpinBox::~Linked2DSpinBox()
{ }

void
Linked2DSpinBox::setBaseValue(const QSizeF &base)
{
    /* Don't allow a 0x0 base to avoid division-by-zero errors */
    if (base.width() == 0 || base.height() == 0)
        return;

    if (base == _base)
        return;

    double w = _xSpin->value();
    double h = _ySpin->value();

    if (linked() && w && h) {
        if (base.width() == _base.width()) {
            h = w * base.height() / base.width();
        } else if (base.height() == _base.height()) {
            w = h * base.width() / base.height();
        } else if (abs((w / h) - (base.width() / base.height())) > 0.0001) {
            double hScaled = h * base.width() / base.height();
            w = (w + hScaled) / 2;
            h = w * base.height() / base.width();
        }
        setValue(QSizeF(w, h));
    }

    if (_displayUnit == UNIT_PERCENT)
        resetScale();

    _base = base;
}

void
Linked2DSpinBox::setBaseUnit(Unit unit)
{
    _baseUnit = unit;
    resetScale();
}

void
Linked2DSpinBox::setDisplayUnit(Unit unit)
{
    _displayUnit = unit;
    resetScale();
}

void
Linked2DSpinBox::linkToggled(bool checked)
{
    if (_link == nullptr) {
        assert(!checked);
        return;
    }

    if (checked)
        _link->setIcon(_linkIcon);
    else
        _link->setIcon(_unlinkIcon);
}

void
Linked2DSpinBox::xChanged(double x)
{
    if (_updating)
        return;

    if (linked()) {
        _updating = true;
        _ySpin->setValue(x * (_base.height() / _base.width()));
        _updating = false;
    }

    emit valueChanged(QSizeF(x, _ySpin->value()));
}

void
Linked2DSpinBox::yChanged(double y)
{
    if (_updating)
        return;

    if (linked()) {
        _updating = true;
        _xSpin->setValue(y * (_base.width() / _base.height()));
        _updating = false;
    }

    emit valueChanged(QSizeF(_xSpin->value(), y));
}

void
Linked2DSpinBox::resetScale()
{
    if (_baseUnit == UNIT_NONE || _displayUnit == UNIT_NONE)
        return;

    if (_displayUnit == UNIT_PERCENT) {
        _xSpin->setScale(_base.width() / 100);
        _ySpin->setScale(_base.height() / 100);
    } else {
        double scale = getUnitConversionFactor(_displayUnit, _baseUnit);
        _xSpin->setScale(scale);
        _ySpin->setScale(scale);
    }
}
