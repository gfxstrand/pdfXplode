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

#include "InputPDF.h"

#include <QtCore/QFile>

InputPDFFile::InputPDFFile(const QString &fileName)
{
    QFile file(fileName);
    if (!file.open(QIODevice::ReadOnly))
        throw std::runtime_error("Failed to open PDF file");
    _bytes = file.readAll();
    if (_bytes.isEmpty())
        throw std::runtime_error("Failed to load PDF file");
    file.close();

    _doc.reset(Poppler::Document::loadFromData(_bytes));
    if (!_doc || _doc->isLocked())
        throw std::runtime_error("Failed to load PDF file");
    _doc->setRenderHint(Poppler::Document::Antialiasing, true);
    _doc->setRenderHint(Poppler::Document::TextAntialiasing, true);
    _doc->setRenderHint(Poppler::Document::TextHinting, true);
}

InputPDFFile::~InputPDFFile()
{ }

unsigned
InputPDFFile::numPages() const
{
    return _doc->numPages();
}

InputPDFPage *
InputPDFFile::getPage(unsigned pageNumber) const
{
    if (pageNumber >= numPages())
        return nullptr;

    return new InputPDFPage(this, pageNumber);
}

InputPDFPage::InputPDFPage(const InputPDFFile *file, unsigned pageNumber) :
    _file(file), _pageNumber(pageNumber)
{
    if (pageNumber >= file->numPages())
        throw std::runtime_error("Invalid page");
    _page.reset(file->_doc->page(pageNumber));
}

InputPDFPage::~InputPDFPage()
{ }

QSize
InputPDFPage::sizeInNativeUnit() const
{
    return _page->pageSize();
}

QImage
InputPDFPage::getQImage(QSize sizeHint) const
{
    if (sizeHint.isEmpty())
        sizeHint = _page->pageSize();

    uint64_t cacheKey =
        static_cast<uint64_t>(sizeHint.width()) |
        (static_cast<uint64_t>(sizeHint.height()) << 32);

    std::unique_lock<std::mutex> lock(_cacheMutex);
    QImage image = _qImageCache.value(cacheKey);
    lock.unlock();

    if (!image.isNull())
        return image;

    double xDpi = (sizeHint.width() * 72) / _page->pageSizeF().width();
    double yDpi = (sizeHint.height() * 72) / _page->pageSizeF().height();

    while (xDpi > 1 && yDpi > 1) {
        image = _page->renderToImage(xDpi, yDpi);

        // If we ask to render an image that's too large, it will return an
        // empty 1x1 image.  Contrary to what the Poppler docs say, it does
        // not return a null image
        if (!image.isNull() && image.size() != QSize(1, 1))
            break;

        xDpi /= 2;
        yDpi /= 2;
    }

    lock.lock();
    // Trim the cache
    while (_qImageCache.count() > 3)
        _qImageCache.remove(_qImageCache.lastKey());
    _qImageCache.insert(cacheKey, image);
    lock.unlock();

    return image;
}

Unit
InputPDFPage::nativeUnit() const
{
    return UNIT_POINTS;
}

QList<Unit>
InputPDFPage::allowedUnits() const
{
    QList<Unit> list;
    list.push_back(UNIT_INCHES);
    list.push_back(UNIT_POINTS);
    return list;
}
