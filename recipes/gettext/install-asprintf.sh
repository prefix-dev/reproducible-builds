#!/bin/bash

set -euxo pipefail

mkdir -p $PREFIX/lib

if [[ "${target_platform}" == osx-* ]]; then
  cp ./gettext-runtime/libasprintf/.libs/libasprintf.*.dylib $PREFIX/lib
else
  cp ./gettext-runtime/libasprintf/.libs/libasprintf.so.* $PREFIX/lib
fi
