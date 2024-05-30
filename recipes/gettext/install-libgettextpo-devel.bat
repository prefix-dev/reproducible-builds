@echo on

if not exist %LIBRARY_PREFIX%\include md %LIBRARY_PREFIX%\include
if errorlevel 1 exit 1

copy gettext-tools\libgettextpo\gettext-po.h %LIBRARY_PREFIX%\include
if errorlevel 1 exit 1

if not exist %LIBRARY_PREFIX%\lib md %LIBRARY_PREFIX%\lib
if errorlevel 1 exit 1

copy gettext-tools\libgettextpo\.libs\gettextpo.dll.lib %LIBRARY_PREFIX%\lib
if errorlevel 1 exit 1

@rem Enforce dynamic linkage
copy gettext-tools\libgettextpo\.libs\gettextpo.dll.lib %LIBRARY_PREFIX%\lib\gettextpo.lib
if errorlevel 1 exit 1
