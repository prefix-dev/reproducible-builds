@echo ON

nmake -f Makefile.MSVC MSVCVER=Win64 comp=msvc asm=yes libmp3lame.dll lame.exe
if errorlevel 1 exit 1

dir
dir output

:REM make sure these are created before we start to copy
mkdir %LIBRARY_PREFIX%\bin
mkdir %LIBRARY_PREFIX%\lib
mkdir %LIBRARY_PREFIX%\include
mkdir %LIBRARY_PREFIX%\include\lame

copy /Y output\libmp3lame.dll %LIBRARY_PREFIX%\bin\libmp3lame.dll
if errorlevel 1 exit 1

copy /Y output\libmp3lame.lib %LIBRARY_PREFIX%\lib\libmp3lame.lib
if errorlevel 1 exit 1

copy /Y include\lame.h %LIBRARY_PREFIX%\include\lame\lame.h
if errorlevel 1 exit 1

copy /Y output\lame.exe %LIBRARY_PREFIX%\bin\lame.exe
if errorlevel 1 exit 1

%LIBRARY_PREFIX%\bin\lame.exe testcase.mp3
if errorlevel 1 exit 1
