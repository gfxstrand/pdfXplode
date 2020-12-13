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

#include <cpp/poppler-page-renderer.h>

#include <cstring>

#define ARRAY_SIZE(a) (sizeof(a) / sizeof(a[0]))
#define MIN(a, b) ((a) < (b) ? (a) : (b))

void
memcpy2d(void *dst, int dst_stride,
         const void *src, int src_stride,
         int height)
{
    int min_stride = MIN(dst_stride, src_stride);
    for (int y = 0; y < height; y++) {
        std::memcpy((char *)dst + y * (size_t)dst_stride,
                    (const char *)src + y * (size_t)src_stride,
                    min_stride);
    }
}

InputPDFFile::InputPDFFile(const QString &fileName)
{
    QFile file(fileName);
    if (!file.open(QIODevice::ReadOnly))
        throw std::runtime_error("Failed to open PDF file");
    _bytes = file.readAll();
    if (_bytes.isEmpty())
        throw std::runtime_error("Failed to load PDF file");
    file.close();

    _doc.reset(poppler::document::load_from_raw_data(_bytes.constData(),
                                                     _bytes.size()));
    if (!_doc || _doc->is_locked())
        throw std::runtime_error("Failed to load PDF file");
}

InputPDFFile::~InputPDFFile()
{ }

unsigned
InputPDFFile::numPages() const
{
    return _doc->pages();
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
    _page.reset(file->_doc->create_page(pageNumber));
}

InputPDFPage::~InputPDFPage()
{ }

QSize
InputPDFPage::sizeInNativeUnit() const
{
    auto rect = _page->page_rect(poppler::media_box);
    assert(rect.x() == 0 && rect.y() == 0);
    return QSize(rect.width(), rect.height());
}

QImage::Format
popplerToQImageFormat(poppler::image::format_enum popplerFormat)
{
    switch (popplerFormat) {
    case poppler::image::format_invalid: return QImage::Format_Invalid;
    case poppler::image::format_mono:    return QImage::Format_Mono;
    case poppler::image::format_rgb24:   return QImage::Format_RGB888;
    case poppler::image::format_argb32:  return QImage::Format_ARGB32;
    case poppler::image::format_gray8:   return QImage::Format_Grayscale8;
#if (QT_VERSION >= QT_VERSION_CHECK(5, 14, 0))
    case poppler::image::format_bgr24:   return QImage::Format_BGR888;
#endif
    default: throw std::runtime_error("Invalid format");
    }
}

QImage
InputPDFPage::getQImage(QSize sizeHint) const
{
    if (sizeHint.isEmpty())
        sizeHint = sizeInNativeUnit();

    uint64_t cacheKey =
        static_cast<uint64_t>(sizeHint.width()) |
        (static_cast<uint64_t>(sizeHint.height()) << 32);

    std::unique_lock<std::mutex> lock(_cacheMutex);
    QImage image = _qImageCache.value(cacheKey);
    lock.unlock();

    if (!image.isNull())
        return image;

    poppler::page_renderer renderer;
    renderer.set_render_hint(poppler::page_renderer::antialiasing, true);
    renderer.set_render_hint(poppler::page_renderer::text_antialiasing, true);
    renderer.set_render_hint(poppler::page_renderer::text_hinting, true);

    double xDpi = (sizeHint.width() * 72) / (double)sizeInNativeUnit().width();
    double yDpi = (sizeHint.height() * 72) / (double)sizeInNativeUnit().height();

    while (xDpi > 1 && yDpi > 1) {
        auto popplerImage = renderer.render_page(_page.get(), xDpi, yDpi);

        image = QImage(popplerImage.width(), popplerImage.height(),
                       popplerToQImageFormat(popplerImage.format()));

        // If our image is too large and allocaiton fails, we'll end up with
        // a null image.
        if (image.isNull()) {
            xDpi /= 2;
            yDpi /= 2;
            continue;
        }

        memcpy2d(image.bits(), image.bytesPerLine(),
                 popplerImage.data(), popplerImage.bytes_per_row(),
                 popplerImage.height());
        break;
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
