#!/bin/bash

set -euxo pipefail

mkdir -p ${PREFIX}/include
cp ./gettext-runtime/intl/libintl.h ${PREFIX}/include/libintl.h

pushd ${PREFIX}/lib
if [[ "${target_platform}" == osx-* ]]; then
  ln -s libintl.*.dylib libintl.dylib
else
  echo "This shouldn't be built on Linux"
  exit 1
  # ln -s libintl.so.0 libintl.so
fi
popd
