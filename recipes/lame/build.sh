#!/bin/bash
# Get an updated config.sub and config.guess
cp $BUILD_PREFIX/share/gnuconfig/config.* .

./configure --prefix=$PREFIX \
	    --disable-dependency-tracking \
	    --disable-debug \
	    --enable-nasm

make -j$CPU_COUNT
make install -j$CPU_COUNT

# test
if [[ "$CONDA_BUILD_CROSS_COMPILATION" != "1" ]]; then
  $PREFIX/bin/lame testcase.mp3
fi
