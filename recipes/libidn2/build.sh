#!/bin/bash
# Get an updated config.sub and config.guess
cp $BUILD_PREFIX/share/gnuconfig/config.* ./build-aux

set -ex
set -o pipefail

./configure --prefix="${PREFIX}" \
    CC_FOR_BUILD="${CC}" \
    --enable-shared \
    --disable-static \
    --disable-gtk-doc \
    --disable-gtk-doc-html \
    --disable-gtk-doc-pdf \
    --disable-nls \
    --disable-code-coverage \
    --without-libiconv-prefix \
    --without-libintl-prefix \
    --without-gcov

make
if [[ "${CONDA_BUILD_CROSS_COMPILATION}" != "1" ]]; then
make check
fi
make install

# Save some space
rm -rf "${PREFIX}/share/info"
rm -rf "${PREFIX}/share/man"
rm -rf "${PREFIX}/share/gtk-doc"
