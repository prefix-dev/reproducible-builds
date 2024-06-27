#!/usr/bin/env bash

set -ex

if [[ "${target_platform}" == "linux-64" ]]; then
  # similar to settings upstream in polars
  export RUSTFLAGS='-C target-feature=+fxsr,+sse,+sse2,+sse3,+ssse3,+sse4.1,+sse4.2,+popcnt,+avx,+fma'
fi

echo rustc --version

if [[ ("${target_platform}" == "win-64" && "${build_platform}" == "linux-64") ]]; then
  # we need to add the generate-import-lib feature since otherwise
  # maturin will expect libpython DSOs at PYO3_CROSS_LIB_DIR
  # which we don't have since we are not able to add python as a host dependency
  cargo feature pyo3 +generate-import-lib --manifest-path py-polars/Cargo.toml
  maturin build --release --strip
  pip install target/wheels/polars*.whl --target $PREFIX/lib/site-packages --platform win_amd64
else
  # Run the maturin build via pip which works for direct and
  # cross-compiled builds.
  python -m pip install . -vv
fi

# The root level Cargo.toml is part of an incomplete workspace
# we need to use the manifest inside the py-polars
cd py-polars
cargo-bundle-licenses --format yaml --output ../THIRDPARTY.yml
