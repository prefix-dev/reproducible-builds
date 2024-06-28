mkdir build && cd build

:: Check the number of cores use by ninja by default
ninja -h

cmake -G "Ninja" ^
    -DCMAKE_BUILD_TYPE=Release ^
    -DCMAKE_INSTALL_PREFIX=%LIBRARY_PREFIX% ^
    -DCMAKE_PREFIX_PATH=%LIBRARY_PREFIX% ^
    -DDART_MSVC_DEFAULT_OPTIONS=ON ^
    -DDART_VERBOSE=ON ^
    -DASSIMP_AISCENE_CTOR_DTOR_DEFINED:BOOL=ON ^
    -DASSIMP_AIMATERIAL_CTOR_DTOR_DEFINED:BOOL=ON ^
    -DDART_TREAT_WARNINGS_AS_ERRORS:BOOL=OFF ^
    -DDART_ENABLE_SIMD:BOOL=OFF ^
    -DDART_BUILD_DARTPY:BOOL=OFF ^
    -DDART_USE_SYSTEM_IMGUI:BOOL=ON ^
    %SRC_DIR%
if errorlevel 1 exit 1

:: Use 2 core to try to avoid out of memory errors
:: See https://github.com/conda-forge/dartsim-feedstock/pull/27#issuecomment-1132570816 (where it was reduced to 4)
:: and https://github.com/conda-forge/dartsim-feedstock/pull/30#issuecomment-1149743621 (where it was reduced to 3)
:: and https://github.com/conda-forge/dartsim-feedstock/pull/38#issuecomment-1553091093 (where it was reduced to 2)
:: and https://github.com/conda-forge/dartsim-feedstock/pull/41#issuecomment-1737995505 (where it was reduced to 1)
ninja -j 1
if errorlevel 1 exit 1

ninja install
if errorlevel 1 exit 1

ctest --output-on-failure
if errorlevel 1 exit 1
