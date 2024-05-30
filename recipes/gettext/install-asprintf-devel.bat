@echo on

if not exist %LIBRARY_PREFIX%\include md %LIBRARY_PREFIX%\include
if errorlevel 1 exit 1

copy gettext-runtime\libasprintf\autosprintf.h %LIBRARY_PREFIX%\include\autosprintf.h
if errorlevel 1 exit 1

if not exist %LIBRARY_PREFIX%\lib md %LIBRARY_PREFIX%\lib
if errorlevel 1 exit 1

copy gettext-runtime\libasprintf\.libs\asprintf.dll.lib %LIBRARY_PREFIX%\lib\asprintf.dll.lib
if errorlevel 1 exit 1

@rem Enforce dynamic linkage
copy gettext-runtime\libasprintf\.libs\asprintf.dll.lib %LIBRARY_PREFIX%\lib\asprintf.lib
if errorlevel 1 exit 1
