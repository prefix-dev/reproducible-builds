#!/bin/sh

mkdir build && cd build

if [[ ${target_platform} == "linux-ppc64le" ]]; then
  NUM_PARALLEL=-j1
else
  NUM_PARALLEL=-j${CPU_COUNT}
fi

if [[ "${target_platform}" == osx-* ]]; then
  # See https://conda-forge.org/docs/maintainer/knowledge_base.html#newer-c-features-with-old-sdk
  CXXFLAGS="${CXXFLAGS} -D_LIBCPP_DISABLE_AVAILABILITY"
fi

cmake ${CMAKE_ARGS} $SRC_DIR \
  -DCMAKE_INSTALL_PREFIX=$PREFIX \
  -DCMAKE_PREFIX_PATH=$PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_LIBDIR=lib \
  -DDART_VERBOSE:BOOL=ON \
  -DDART_TREAT_WARNINGS_AS_ERRORS:BOOL=OFF \
  -DDART_ENABLE_SIMD:BOOL=OFF \
  -DDART_BUILD_DARTPY:BOOL=OFF \
  -DDART_USE_SYSTEM_IMGUI:BOOL=ON

make ${NUM_PARALLEL}
make ${NUM_PARALLEL} install

if [ ${target_platform} != "linux-ppc64le" ]; then
  make ${NUM_PARALLEL} tests
  if [[ "${CONDA_BUILD_CROSS_COMPILATION:-}" != "1" || "${CROSSCOMPILING_EMULATOR}" != "" ]]; then
    ctest --output-on-failure
  fi
fi
