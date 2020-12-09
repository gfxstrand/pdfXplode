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

#include <QtWidgets/QDoubleSpinBox>

class ScaledSpinBox : public QWidget
{
    Q_OBJECT;

public:
    ScaledSpinBox(QWidget *parent);
    virtual ~ScaledSpinBox();

    inline double minimum() { return _raw->minimum() * _scale; }
    inline double maximum() { return _raw->maximum() * _scale; }
    inline double singleStep() { return _raw->singleStep() * _scale; }
    inline double value() { return _raw->value() * _scale; }
    inline double scale() { return _scale; }

    inline void setMinimum(double min) { _raw->setMinimum(min / _scale); }
    inline void setMaximum(double max) { _raw->setMaximum(max / _scale); }
    inline void setSingleStep(double val) { _raw->setSingleStep(val / _scale); }
    inline void setValue(double val) { _raw->setValue(val / _scale); }
    void setScale(double scale);

private:
    QDoubleSpinBox *_raw;
    double _scale;

signals:
    void valueChanged(double value);

private slots:
    void rawValueChanged(double value);
};
