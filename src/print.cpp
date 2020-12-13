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

#include <podofo.h>

#include <stdexcept>

QList<QLine>
getRegistrationMarkLines(QPageLayout pageLayout)
{
    auto page = pageLayout.fullRectPoints();
    auto margin = pageLayout.marginsPoints();

    // Get ourselves some nice abbreviations
    unsigned pw = page.width();
    unsigned ph = page.height();
    unsigned ml = margin.left();
    unsigned mr = margin.right();
    unsigned mt = margin.top();
    unsigned mb = margin.bottom();

    // A caution factor of 90% to keep our registration lines from
    // running into the main page area
    float cf = 0.9f;

    QList<QLine> lines;
    lines.push_back(QLine(0, mt, ml * cf, mt));
    lines.push_back(QLine(ml, 0, ml, mt * cf));
    lines.push_back(QLine(pw, mt, pw - mr * cf, mt));
    lines.push_back(QLine(pw - mr, 0, pw - mr, mt * cf));
    lines.push_back(QLine(0, ph - mb, ml * cf, ph - mb));
    lines.push_back(QLine(ml, ph, ml, ph - mb * cf));
    lines.push_back(QLine(pw, ph - mb, pw - mr * cf, ph - mb));
    lines.push_back(QLine(pw - mr, ph, pw - mr, ph - mb * cf));

    return lines;
}

void
paintRegistrationMarks(QPrinter *printer, QPainter &painter)
{
    auto lines = getRegistrationMarkLines(printer->pageLayout());

    QPen pen;
    pen.setStyle(Qt::SolidLine);
    pen.setWidth(1);
    pen.setBrush(Qt::black);

    painter.save();
    painter.setPen(pen);
    for (auto line : lines)
        painter.drawLine(line);
    painter.restore();
}

bool
setupPainter(QPrinter *printer, QPainter &painter)
{
    // We'll deal with margins ourselves, thank you.
    printer->setFullPage(true);

    if (!painter.begin(printer))
        throw std::runtime_error("Failed to open printer, is it writable?");

#if (QT_VERSION >= QT_VERSION_CHECK(5, 13, 0))
    painter.setRenderHint(QPainter::LosslessImageRendering, true);
#endif

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
generatePDFFromPDF(QString outFileName, QPageLayout outPageLayout,
                   const InputPDFPage *inPage,
                   const QRect &cropRect, const QSize &outSize,
                   bool trim, bool registrationMarks)
{
    auto fullRect = outPageLayout.fullRectPoints();
    auto margin = outPageLayout.marginsPoints();

    int printWidth = fullRect.width() - margin.left() - margin.right();
    int printHeight = fullRect.height() - margin.top() - margin.bottom();

    int numPagesX = divRoundUp(outSize.width(), printWidth);
    int numPagesY = divRoundUp(outSize.height(), printHeight);

    QByteArray inRawBytes = inPage->pdfFile()->rawBytes();
    PoDoFo::PdfMemDocument inDoc;
    inDoc.LoadFromBuffer(inRawBytes.constData(), inRawBytes.size());
    inDoc.EmbedSubsetFonts();

    PoDoFo::PdfMemDocument outDoc;
    PoDoFo::PdfRect outPdfPageSize(0, 0, fullRect.width(), fullRect.height());

    PoDoFo::PdfXObject inPageXObj(inDoc, inPage->pageNumber(), &outDoc);

    for (int y = 0; y < numPagesY; y++) {
        for (int x = 0; x < numPagesX; x++) {
            PoDoFo::PdfPage *outPdfPage = outDoc.CreatePage(outPdfPageSize);
            PoDoFo::PdfPainter painter;
            painter.SetPage(outPdfPage);

            double xt = x * printWidth;
            double yt = y * printHeight;

            // PDF coordinates start at the bottom-left but everything
            // else is top-down so flip the Y transform
            yt = outSize.height() - yt - printHeight;

            QTransform xform;
            xform.translate(margin.left(), margin.bottom());
            xform.translate(-xt, -yt);
            xform.scale(outSize.width() / (double)cropRect.width(),
                        outSize.height() / (double)cropRect.height());
            xform.translate(-cropRect.x(), -cropRect.y());

            painter.Save();
            assert(xform.isAffine() && xform.m12() == 0 && xform.m21() == 0);
            painter.DrawXObject(xform.m31(), xform.m32(), &inPageXObj,
                                xform.m11(), xform.m22());
            painter.Restore();

            if (trim) {
                painter.SetGray(1.0);
                // Remember!  Coordinates in PDFs start at the bottom-left
                // and we don't have QPainter helping flip them around
                painter.Rectangle(0, 0, margin.left(), fullRect.height());
                painter.Rectangle(0, 0, fullRect.width(), margin.bottom());
                painter.Rectangle(fullRect.width() - margin.right(), 0,
                                  margin.right(), fullRect.height());
                painter.Rectangle(0, fullRect.height() - margin.top(),
                                  fullRect.width(), fullRect.height());
                painter.Fill();
            }

            if (registrationMarks) {
                painter.SetStrokeWidth(1.0);
                painter.SetStrokingGray(0.0);

                auto lines = getRegistrationMarkLines(outPageLayout);
                for (auto line : lines) {
                    // Remember!  Coordinates in PDFs start at the bottom-left
                    // and we don't have QPainter helping flip them around
                    painter.DrawLine(line.x1(), fullRect.height() - line.y1(),
                                     line.x2(), fullRect.height() - line.y2());
                }
            }

            painter.FinishPage();
        }
    }

    outDoc.Write(outFileName.toUtf8().data());
}

void
printInputPage(QPrinter *printer, const InputPage *inPage,
               const QRect &cropRect, const QSize &outSize,
               bool trim, bool registrationMarks)
{
    if (printer->outputFormat() == QPrinter::PdfFormat &&
        !printer->outputFileName().isEmpty() &&
        dynamic_cast<const InputPDFPage *>(inPage)) {
        // In this case, we're outputting a PDF from another PDF.  We can
        // output a higher quality PDF if we do it manually with PoDoFo.
        printer->abort();
        generatePDFFromPDF(printer->outputFileName(), printer->pageLayout(),
                           dynamic_cast<const InputPDFPage *>(inPage),
                           cropRect, outSize, trim, registrationMarks);
        return;
    }

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

void
testGeneratePDF(const QString &inFileName, unsigned inPageNumber,
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

    generatePDFFromPDF(outFileName, pageLayout, inPage.get(),
                      cropRect, outSize, trim, registrationMarks);
}
