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

#include "UnitsComboBox.h"

UnitsComboBox::UnitsComboBox(QWidget *parent) :
    QComboBox(parent)
{
    setEditable(false);
    connect(this, QOverload<int>::of(&QComboBox::currentIndexChanged),
            this, &UnitsComboBox::parentIndexChanged);
    _updating = false;
}

UnitsComboBox::~UnitsComboBox()
{ }

Unit
UnitsComboBox::value() const
{
    int i = currentIndex();
    if (i < 0)
        return UNIT_NONE;
    return _units[currentIndex()];
}

void
UnitsComboBox::setValue(Unit u)
{
    int i = _units.indexOf(u);
    if (i < 0)
        throw std::runtime_error("Invalid unit");
    setCurrentIndex(i);
}

void
UnitsComboBox::setAvailableUnits(const QList<Unit>& units)
{
    Unit oldValue = value();

    _updating = true;
    clear();

    _units = units;

    QStringList strings;
    for (auto u : units)
        strings.push_back(getUnitString(u));
    addItems(strings);

    int i = _units.indexOf(oldValue);
    if (i >= 0) {
        setCurrentIndex(i);
    } else {
        setCurrentIndex(0);
        emit valueChanged(_units[0]);
    }

    _updating = false;
}

void
UnitsComboBox::parentIndexChanged(int index)
{
    if (!_updating)
        emit valueChanged(_units[index]);
}
