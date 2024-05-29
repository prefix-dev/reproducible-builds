@echo on

if not exist %LIBRARY_PREFIX%\bin md %LIBRARY_PREFIX%\bin
if errorlevel 1 exit 1

copy gettext-runtime\libasprintf\.libs\asprintf-0.dll %LIBRARY_PREFIX%\bin
if errorlevel 1 exit 1
