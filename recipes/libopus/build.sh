#!/bin/bash

echo "PACKAGE_VERSION=${PKG_VERSION}" > package_version

./autogen.sh

./configure --prefix=${PREFIX} --disable-static --disable-doc

make -j${CPU_COUNT}

make install
