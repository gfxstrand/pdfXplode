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

#include "InputPage.h"

#include <QtCore/QList>
#include <QtCore/QString>

class InputImage : public InputPage
{
public:
    InputImage(const QString &fileName);
    virtual ~InputImage();

    virtual QSize sizeInNativeUnit() const;
    virtual QImage getQImage(QSize sizeHint) const;

    virtual Unit nativeUnit() const;
    virtual QList<Unit> allowedUnits() const;

private:
    QImage qImage;
};
