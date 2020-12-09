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

project(
  'pdfXplode',
  ['cpp'],
  license : 'GPL-3.0-or-later',
)

qt5 = import('qt5')
qt5_dep = dependency('qt5', modules: ['Core', 'Gui', 'Widgets', 'PrintSupport'])

headers = [
  'src/CropWidget.h',
  'src/InputImage.h',
  'src/InputPage.h',
  'src/Linked2DSpinBox.h',
  'src/print.h',
  'src/ScaledSpinBox.h',
  'src/Unit.h',
]

sources = [
  'src/CropWidget.cpp',
  'src/InputImage.cpp',
  'src/InputPage.cpp',
  'src/Linked2DSpinBox.cpp',
  'src/main.cpp',
  'src/print.cpp',
  'src/ScaledSpinBox.cpp',
]

inc = include_directories('src')
moc_files = qt5.preprocess(moc_headers : headers,
                           include_directories: inc,
                           dependencies: qt5_dep)
executable('pdfXplode', sources, moc_files,
           include_directories: inc,
           install : true,
           dependencies : [qt5_dep])
