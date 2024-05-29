#!/bin/bash

set -euxo pipefail

mkdir -p $PREFIX/lib

if [[ "${target_platform}" == osx-* ]]; then
  cp ./gettext-tools/libgettextpo/.libs/libgettextpo.*.dylib $PREFIX/lib
else
  cp ./gettext-tools/libgettextpo/.libs/libgettextpo.so.* $PREFIX/lib
fi
