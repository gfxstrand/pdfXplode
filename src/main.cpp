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

#include "MainWindow.h"

#include <QtGui/QPageLayout>
#include <QtWidgets/QApplication>

QDataStream &operator<<(QDataStream &out, const QPageSize &pageSize)
{
    return out << pageSize.sizePoints();
}

QDataStream &operator>>(QDataStream &in, QPageSize &pageSize)
{
    QSize sizePoints;
    in >> sizePoints;
    pageSize = QPageSize(sizePoints);
    return in;
}

QDataStream &operator<<(QDataStream &out, const QPageLayout &pageLayout)
{
    return out << pageLayout.pageSize()
               << (int)pageLayout.orientation()
               << pageLayout.margins()
               << (int)pageLayout.units()
               << pageLayout.minimumMargins();
}

QDataStream &operator>>(QDataStream &in, QPageLayout &pageLayout)
{
    QPageSize pageSize;
    int orientation, units;
    QMarginsF margins, minMargins;
    in >> pageSize >> orientation >> margins >> units >> minMargins;
    pageLayout = QPageLayout(pageSize, (QPageLayout::Orientation)orientation,
                             margins, (QPageLayout::Unit)units, minMargins);
    return in;
}

int
main(int argc, char **argv)
{
    QCoreApplication::setOrganizationName("jlekstrand.net");
    QCoreApplication::setOrganizationDomain("jlekstrand.net");
    QCoreApplication::setApplicationName("pdfXtract");

    QApplication::setAttribute(Qt::AA_EnableHighDpiScaling);
    QApplication::setAttribute(Qt::AA_UseHighDpiPixmaps);
    QApplication app(argc, argv);

    qRegisterMetaTypeStreamOperators<QPageSize>("QPageSize");
    qRegisterMetaTypeStreamOperators<QPageLayout>("QPageLayout");

    MainWindow window;
    window.show();

    return app.exec();
}
