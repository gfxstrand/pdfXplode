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

#include <poppler-qt5.h>

#include <memory>
#include <mutex>
#include <thread>

class InputPDFPage;

class InputPDFFile
{
    friend class InputPDFPage;

public:
    InputPDFFile(const QString &fileName);
    virtual ~InputPDFFile();

    unsigned numPages() const;
    InputPDFPage *getPage(unsigned pageNumber) const;

private:
    std::unique_ptr<Poppler::Document> _doc;
};

class InputPDFPage : public InputPage
{
public:
    InputPDFPage(const InputPDFFile *file, unsigned pageNumber);
    virtual ~InputPDFPage();

    virtual QSize sizeInNativeUnit() const;
    virtual QImage getQImage(QSize sizeHint = QSize(0, 0)) const;

    virtual Unit nativeUnit() const;
    virtual QList<Unit> allowedUnits() const;

private:
    const InputPDFFile *_file;
    unsigned _pageNumber;

    std::unique_ptr<Poppler::Page> _page;

    mutable std::mutex _cacheMutex;
    mutable QMap<uint64_t, QImage> _qImageCache;
};
