REM Based on bld.bat from pysyntect-feedstock
REM https://github.com/conda-forge/pysyntect-feedstock/

REM Create temp folder
mkdir tmpbuild_%PY_VER%
set TEMP=%CD%\tmpbuild_%PY_VER%

REM Print Rust version
rustc --version

REM set UTF-8 mode by default
chcp 65001
set PYTHONUTF8=1
set PYTHONIOENCODING="UTF-8"

REM https://github.com/rust-lang/cargo/issues/10583#issuecomment-1129997984
set CARGO_NET_GIT_FETCH_WITH_CLI=true

REM dont enable cross-compile
set MATURIN_SETUP_ARGS=--no-default-features --features=cli-completion,log,scaffolding,upload,native-tls

%PYTHON% -m pip install . --no-deps --ignore-installed -vv
