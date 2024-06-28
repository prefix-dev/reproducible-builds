#!/bin/bash
set -e
set -x

# Get an updated config.sub and config.guess
cp $BUILD_PREFIX/share/gnuconfig/config.* ./tool

# We don't want to leak the $BUILD_PREFIX into the final output
export CC=$(basename $CC)
export CPP=$(basename $CPP)
export CXX=$(basename $CXX)
export STRIP=$(basename $STRIP)
export OBJDUMP=$(basename $OBJDUMP)
export AS=$(basename $AS)
export AR=$(basename $AR)
export RANLIB=$(basename $RANLIB)
export LD=$(basename $LD)

# we have to use `llvm-nm` instead of `nm` for the ruby build
# because of the Rust YJIT dependency
export NM=llvm-nm

autoconf

export ZERO_AR_DATE=1

./configure \
  --prefix="${PREFIX}" \
  --disable-install-doc \
  --enable-load-relative \
  --enable-shared \
  --with-libffi-dir="$PREFIX" \
  --with-libyaml-dir="$PREFIX" \
  --with-openssl-dir="$PREFIX" \
  --with-readline-dir="$PREFIX" \
  --with-zlib-dir="$PREFIX"

make -j ${CPU_COUNT}
# make check works locally on Linux, but not on CI Nodes, issue seems related to IPv6 and closed ports
# make check
make install

mkdir -p $PREFIX/etc
mkdir -p $PREFIX/share/rubygems/
ln -s "${PREFIX}/bin/ruby" "${PREFIX}/share/rubygems/ruby"

echo "gemhome: ${PREFIX}/share/rubygems" > $PREFIX/etc/gemrc

# Copy the [de]activate scripts to $PREFIX/etc/conda/[de]activate.d.
# This will allow them to be run on environment activation.
# for CHANGE in "activate" "deactivate"
# do
#     mkdir -p "${PREFIX}/etc/conda/${CHANGE}.d"
#     cp "${RECIPE_DIR}/${CHANGE}.sh" "${PREFIX}/etc/conda/${CHANGE}.d/${PKG_NAME}_${CHANGE}.sh"
#     cp "${RECIPE_DIR}/${CHANGE}.ps1" "${PREFIX}/etc/conda/${CHANGE}.d/${PKG_NAME}_${CHANGE}.ps1"
# done
