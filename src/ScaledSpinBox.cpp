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

#include "ScaledSpinBox.h"

#include <QtWidgets/QHBoxLayout>

ScaledSpinBox::ScaledSpinBox(QWidget *parent) :
    QWidget(parent)
{
    _raw = new QDoubleSpinBox(this);
    connect(_raw, QOverload<double>::of(&QDoubleSpinBox::valueChanged),
            this, &ScaledSpinBox::rawValueChanged);
    _scale = 1.0;

    auto layout = new QHBoxLayout(this);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->addWidget(_raw);
    this->setLayout(layout);
}

ScaledSpinBox::~ScaledSpinBox()
{ }

void
ScaledSpinBox::rawValueChanged(double rawValue)
{
    emit valueChanged(rawValue * _scale);
}

void
ScaledSpinBox::setScale(double scale)
{
    double savedMin = minimum();
    double savedMax = maximum();
    double savedStep = singleStep();
    double savedValue = value();

    _scale = scale;

    setMinimum(savedMin);
    setMaximum(savedMax);
    setSingleStep(savedStep);
    setValue(savedValue);
}
