#!/bin/bash

set -euxo pipefail

mkdir -p $PREFIX/lib

if [[ "${target_platform}" == osx-* ]]; then
  cp ./gettext-runtime/intl/.libs/libintl.*.dylib $PREFIX/lib
else
  cp ./gettext-runtime/intl/.libs/libintl.so.* $PREFIX/lib
fi
