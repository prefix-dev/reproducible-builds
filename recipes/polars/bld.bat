@echo on
set "PYO3_PYTHON=%PYTHON%"

sed -i "s/lto = ""fat""/lto = ""thin""/g" Cargo.toml
if errorlevel 1 exit 1

set "CMAKE_GENERATOR=NMake Makefiles"
@rem set "RUSTFLAGS=-C codegen-units=4"
maturin build -v --jobs 1 --release --strip --manylinux off --interpreter=%PYTHON%
if errorlevel 1 exit 1

FOR /F "delims=" %%i IN ('dir /s /b target\wheels\*.whl') DO set polars_wheel=%%i
%PYTHON% -m pip install --ignore-installed --no-deps %polars_wheel% -vv
if errorlevel 1 exit 1

REM The root level Cargo.toml is part of an incomplete workspace
REM we need to use the manifest inside the py-polars
cd py-polars
cargo-bundle-licenses --format yaml --output ../THIRDPARTY.yml
