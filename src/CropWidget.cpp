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

#include "CropWidget.h"

#include <QtWidgets/QGraphicsPixmapItem>
#include <QtWidgets/QGraphicsRectItem>

#include <cassert>

CropWidget::CropWidget(QWidget *parent) :
    QGraphicsView(parent),
    _inPage(nullptr),
    _pixmapItem(nullptr),
    _cropRectItem(nullptr)
{
    _scene = new QGraphicsScene(this);
    _scene->setBackgroundBrush(QBrush(Qt::gray));
    setScene(_scene);
}

CropWidget::~CropWidget()
{ }

void
CropWidget::setCropRect(QRect rect)
{
    _cropRect = rect;
    if (_cropRectItem)
        _cropRectItem->setRect(rect);
}

void
CropWidget::setCropOrig(QPoint orig)
{
    setCropRect(QRect(orig, _cropRect.size()));
}

void
CropWidget::setCropSize(QSize size)
{
    setCropRect(QRect(_cropRect.topLeft(), size));
}

void
CropWidget::setInputPage(InputPage *inPage)
{
    _inPage = inPage;
    reload();
}

void
CropWidget::reload()
{
    _scene->clear();
    _pixmapItem = nullptr;
    _cropRectItem = nullptr;
    if (!_inPage)
        return;

    // We like 96 DPI
    QSize pageSize = _inPage->sizeInNativeUnits();
    QSize preferredSize = (pageSize * 96.0) / 72.0;
    _image = _inPage->getQImage(preferredSize);
    _pixmapItem = _scene->addPixmap(QPixmap::fromImage(_image));

    // Assume it scales the same in both directions
    assert(pageSize.width() * _image.height() ==
           pageSize.height() * _image.width());

    _pixmapItem->setScale(pageSize.width() / (double)_image.width());

    // Set the scale for the whole scene
    setSceneRect(QRectF(QRect(QPoint(0, 0), pageSize)));
    setTransform(QTransform().scale(96.0 / 72.0, 96.0 / 72.0));

    // Add the crop rect
    QPen cropPen;
    cropPen.setStyle(Qt::SolidLine);
    cropPen.setWidth(1);
    cropPen.setBrush(Qt::red);
    cropPen.setCapStyle(Qt::RoundCap);
    cropPen.setJoinStyle(Qt::RoundJoin);
    _cropRectItem = _scene->addRect(_cropRect, cropPen, QBrush(Qt::NoBrush));
}
