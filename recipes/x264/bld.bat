@ECHO ON

rem Set the assembler to `nasm`
set AS=%BUILD_PREFIX%\Library\bin\nasm.exe

:REM --system-libx264 makes windows choose the shared library for the x264 cli argument
:REM instead of the static library
bash ./configure ^
  --enable-pic ^
  --enable-shared ^
  --system-libx264 ^
  --prefix=%LIBRARY_PREFIX%
if errorlevel 1 exit 1

make -j%CPU_COUNT%
if errorlevel 1 exit 1

make install
if errorlevel 1 exit 1

move %LIBRARY_LIB%\libx264.dll.lib %LIBRARY_LIB%\libx264.lib 
if errorlevel 1 exit 1
