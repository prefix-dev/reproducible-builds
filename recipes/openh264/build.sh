#!/bin/bash

set -x

if [[ "$CONDA_BUILD_CROSS_COMPILATION" == 1 ]]; then
  if [[ "$ARCH" == "64" ]]; then
    ARCH=x86_64
  fi
  sed -i.bak "s/ARCH=.*/ARCH=$ARCH/g" Makefile
fi

make PREFIX=$PREFIX -j${CPU_COUNT}
make PREFIX=$PREFIX install

mkdir -p -m755 -v "$PREFIX"/bin
install -m755 -v h264dec "$PREFIX"/bin/h264dec
install -m755 -v h264enc "$PREFIX"/bin/h264enc
