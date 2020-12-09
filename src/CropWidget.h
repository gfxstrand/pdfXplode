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

#include <QtWidgets/QGraphicsView>

class CropWidget : public QGraphicsView
{
    Q_OBJECT;

public:
    CropWidget(QWidget *parent);
    virtual ~CropWidget();

public slots:
    void setCropRect(QRect rect);
    void setCropOrig(QPoint orig);
    void setCropSize(QSize size);
    void setInputPage(InputPage *inPage);

private:
    void reload();

    QGraphicsScene *_scene;
    InputPage *_inPage;

    QImage _image;
    QGraphicsPixmapItem *_pixmapItem;

    QRect _cropRect;
    QGraphicsRectItem *_cropRectItem;
};
