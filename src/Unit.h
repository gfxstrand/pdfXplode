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

#include <QtCore/QString>

#include <stdexcept>

enum Unit
{
    UNIT_NONE,
    UNIT_INCHES,
    UNIT_PERCENT,
    UNIT_PIXELS,
    UNIT_POINTS,
};

inline QString
getUnitString(Unit u)
{
    switch (u) {
    case UNIT_INCHES:   return "inches";
    case UNIT_PERCENT:  return "percent";
    case UNIT_PIXELS:   return "pixels";
    case UNIT_POINTS:   return "points";
    default:            throw std::runtime_error("Invalid unit");
    }
}

inline double
getUnitConversionFactor(Unit a, Unit b)
{
    if (a == b)
        return 1;

    if (a == UNIT_INCHES) {
        switch (b) {
        case UNIT_POINTS:
            return 72;
        case UNIT_PIXELS:
            return 96;
        default:
            throw std::runtime_error("Invalid unit conversion");
        }
    } else if (b == UNIT_INCHES) {
        return 1 / getUnitConversionFactor(b, a);
    } else {
        return getUnitConversionFactor(a, UNIT_INCHES) *
               getUnitConversionFactor(UNIT_INCHES, b);
    }
}
