#!/bin/bash

set -euxo pipefail

mkdir -p ${PREFIX}/include
cp ./gettext-tools/libgettextpo/gettext-po.h ${PREFIX}/include/gettext-po.h

pushd ${PREFIX}/lib
if [[ "${target_platform}" == osx-* ]]; then
  ln -s libgettextpo.*.dylib libgettextpo.dylib
else
  test -f libgettextpo.so.0
  ln -s libgettextpo.so.0 libgettextpo.so
fi
popd

