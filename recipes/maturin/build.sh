# Based on the build.sh for the pysyntect-feedstock recipe.
# https://github.com/conda-forge/pysyntect-feedstock/
set -ex

# Set conda CC as custom CC in Rust
export CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_LINKER=$CC
export CARGO_TARGET_X86_64_APPLE_DARWIN_LINKER=$CC
export CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER=$CC

# Print Rust version
rustc --version

# https://github.com/rust-lang/cargo/issues/10583#issuecomment-1129997984
export CARGO_NET_GIT_FETCH_WITH_CLI=true

export OPENSSL_NO_VENDOR=1
export MATURIN_SETUP_ARGS="--no-default-features --features=cli-completion,log,scaffolding,upload,native-tls" # dont enable cross-compile

# Install wheel manually
$PYTHON -m pip install . --no-deps --ignore-installed -vv
