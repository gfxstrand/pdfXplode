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

#include "print.h"

#include "InputImage.h"
#include "InputPDF.h"

#include <QtGui/QPainter>
#include <QtGui/QPen>

#include <stdexcept>

void
paintRegistrationMarks(QPrinter *printer, QPainter &painter)
{
    auto page = printer->pageLayout().fullRectPoints();
    auto margin = printer->pageLayout().marginsPoints();

    // Get ourselves some nice abbreviations
    unsigned pw = page.width();
    unsigned ph = page.height();
    unsigned ml = margin.left();
    unsigned mr = margin.right();
    unsigned mt = margin.top();
    unsigned mb = margin.bottom();

    // A caution factor of 90% to keep our registration lines from
    // running into the main page area
    float cf = 0.9;

    QPen pen;
    pen.setStyle(Qt::SolidLine);
    pen.setWidth(1);
    pen.setBrush(Qt::black);

    painter.save();
    painter.setPen(pen);
    painter.drawLine(0, mt, ml * cf, mt);
    painter.drawLine(ml, 0, ml, mt * cf);
    painter.drawLine(pw, mt, pw - mr * cf, mt);
    painter.drawLine(pw - mr, 0, pw - mr, mt * cf);
    painter.drawLine(0, ph - mb, ml * cf, ph - mb);
    painter.drawLine(ml, ph, ml, ph - mb * cf);
    painter.drawLine(pw, ph - mb, pw - mr * cf, ph - mb);
    painter.drawLine(pw - mr, ph, pw - mr, ph - mb * cf);
    painter.restore();
}

bool
setupPainter(QPrinter *printer, QPainter &painter)
{
    // We'll deal with margins ourselves, thank you.
    printer->setFullPage(true);

    if (!painter.begin(printer))
        throw std::runtime_error("Failed to open printer, is it writable?");

    painter.setRenderHint(QPainter::LosslessImageRendering, true);

    auto pageSizePoints = printer->pageLayout().fullRectPoints().size();
    auto pageSizeLogical = QSize(
        (pageSizePoints.width() * printer->logicalDpiX()) / 72,
        (pageSizePoints.height() * printer->logicalDpiY()) / 72);

    painter.setWindow(QRect(QPoint(0, 0), pageSizePoints));
    painter.setViewport(QRect(QPoint(0, 0), pageSizeLogical));

    return true;
}

int divRoundUp(int n, int d)
{
    return (n + (d - 1)) / d;
}

void
printInputPage(QPrinter *printer, const InputPage *inPage,
               const QRect &cropRect, const QSize &outSize,
               bool trim, bool registrationMarks)
{
    QPainter painter;
    setupPainter(printer, painter);

    auto fullRect = printer->pageLayout().fullRectPoints();
    auto margin = printer->pageLayout().marginsPoints();

    int printWidth = fullRect.width() - margin.left() - margin.right();
    int printHeight = fullRect.height() - margin.top() - margin.bottom();

    int numPagesX = divRoundUp(outSize.width(), printWidth);
    int numPagesY = divRoundUp(outSize.height(), printHeight);

    auto inPageSize = inPage->sizeInNativeUnit();
    auto imageSizeHint = QSize(
        (inPageSize.width() *
         painter.device()->physicalDpiX() *
         outSize.width()) /
        (cropRect.width() * 72),
        (inPageSize.height() *
         painter.device()->physicalDpiY() *
         outSize.height()) /
        (cropRect.height() * 72));

    QImage image = inPage->getQImage(imageSizeHint);

    for (int y = 0; y < numPagesY; y++) {
        for (int x = 0; x < numPagesX; x++) {
            if (x > 0 || y > 0) {
                if (!printer->newPage())
                    throw std::runtime_error("Failed to flush the page");
            }

            if (registrationMarks)
                paintRegistrationMarks(printer, painter);

            painter.save();

            if (trim) {
                painter.setClipRect(margin.left(), margin.top(),
                                    printWidth, printHeight);
            }

            painter.translate(margin.left(), margin.top());
            painter.translate(-x * printWidth, -y * printHeight);
            painter.scale(outSize.width() / (double)cropRect.width(),
                          outSize.height() / (double)cropRect.height());
            painter.translate(-cropRect.x(), -cropRect.y());

            painter.scale(inPageSize.width() / (double)image.size().width(),
                          inPageSize.height() / (double)image.size().height());
            painter.drawImage(0, 0, image);

            painter.restore();
        }
    }

    painter.end();
}

void
testPrintImage(const QString &inFileName, const QString &outFileName,
               const QRect &cropRect, const QSize &outSize,
               bool trim, bool registrationMarks)
{
    InputImage inImage(inFileName);

    QPageLayout pageLayout(QPageSize(QPageSize::Letter),
                           QPageLayout::Portrait,
                           QMarginsF(0.5, 0.5, 0.5, 0.5),
                           QPageLayout::Inch);

    QPrinter printer;
    printer.setOutputFormat(QPrinter::PdfFormat);
    printer.setPageLayout(pageLayout);
    printer.setColorMode(QPrinter::Color);
    printer.setOutputFileName(outFileName);

    printInputPage(&printer, &inImage, cropRect, outSize,
                   trim, registrationMarks);
}

void
testPrintPDF(const QString &inFileName, unsigned inPageNumber,
             const QString &outFileName,
             const QRect &cropRect, const QSize &outSize,
             bool trim, bool registrationMarks)
{
    std::unique_ptr<InputPDFFile> inPDF(new InputPDFFile(inFileName));
    std::unique_ptr<InputPDFPage> inPage(inPDF->getPage(inPageNumber));

    QPageLayout pageLayout(QPageSize(QPageSize::Letter),
                           QPageLayout::Portrait,
                           QMarginsF(0.5, 0.5, 0.5, 0.5),
                           QPageLayout::Inch);

    QPrinter printer;
    printer.setOutputFormat(QPrinter::PdfFormat);
    printer.setPageLayout(pageLayout);
    printer.setColorMode(QPrinter::Color);
    printer.setOutputFileName(outFileName);

    printInputPage(&printer, inPage.get(), cropRect, outSize,
                   trim, registrationMarks);
}
