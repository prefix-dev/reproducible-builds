#!/bin/bash

export ZERO_AR_DATE=1

# Get an updated config.sub and config.guess
cp $BUILD_PREFIX/share/libtool/build-aux/config.* .

if [[ ${CC} =~ .*gcc.* && ${c_compiler} =~ .*toolchain.* ]]; then
    export CFLAGS="${CFLAGS} -std=c99 "
fi
if [[ "$target_platform" == "osx-arm64" ]]; then
  CONFIGURE_ARGS="$CONFIGURE_ARGS --disable-assembler"
fi
# See: https://gitlab.com/gnutls/gnutls/issues/665
export CPPFLAGS="${CPPFLAGS//-DNDEBUG/}"

# Building with conda-forge gmp causes a strange segfault.
# Using mini-gmp seems to solve the issue and gnutls still works.
# --disable-openssl: do not include openssl glue in the benchmark program
./configure --prefix="${PREFIX}"              \
            --libdir="${PREFIX}/lib/"         \
            --with-lib-path="${PREFIX}/lib/"  \
            $CONFIGURE_ARGS \
            --disable-openssl \
            --disable-static \
            --enable-mini-gmp || { cat config.log; exit 1; }
make -j${CPU_COUNT} ${VERBOSE_AT}
make install ${VERBOSE_AT}
if [[ "${CONDA_BUILD_CROSS_COMPILATION}" != "1" ]]; then
  make check
fi
