@echo on

meson setup builddir ^
  --prefix="%LIBRARY_PREFIX%" ^
  --buildtype=release ^
  --backend=ninja ^
  -Dtests=disabled
if errorlevel 1 exit 1

 %BUILD_PREFIX%\Scripts\meson.exe configure builddir
 if errorlevel 1 exit 1

 ninja -v -C builddir -j %CPU_COUNT%
 if errorlevel 1 exit 1

 ninja -C builddir install -j %CPU_COUNT%
 if errorlevel 1 exit 1

 copy /Y builddir\codec\console\enc\h264enc.exe %LIBRARY_PREFIX%\bin\h264enc.exe
 copy /Y builddir\codec\console\dec\h264dec.exe %LIBRARY_PREFIX%\bin\h264dec.exe
