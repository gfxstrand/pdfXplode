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

INCHES = 'inches'
PERCENT = 'percent'
POINTS = 'points'

class UnitConversionError(ValueError):
    def __init__(self, a, b):
        errStr = a + " to " + b + " is an invalid unit conversion"
        super(UnitConversionError, self).__init__(errStr)

def getConversionFactor(a, b):
    """Returns the unit conversion factor for converting from a to b"""
    if a == b:
        return 1

    if a == INCHES:
        if b == POINTS:
            return 72
        else:
            raise UnitConversionError(a, b)
    elif b == INCHES:
        return 1 / getConversionFactor(b, a)
    else:
        return getConversionFactor(a, INCHES) * getConversionFactor(INCHES, b)
