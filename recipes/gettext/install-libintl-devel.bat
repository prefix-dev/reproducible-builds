@echo on

if not exist %LIBRARY_PREFIX%\include md %LIBRARY_PREFIX%\include
if errorlevel 1 exit 1

copy gettext-runtime\intl\libintl.h %LIBRARY_PREFIX%\include\libintl.h
if errorlevel 1 exit 1

if not exist %LIBRARY_PREFIX%\lib md %LIBRARY_PREFIX%\lib
if errorlevel 1 exit 1

copy gettext-runtime\intl\.libs\intl.dll.lib %LIBRARY_PREFIX%\lib
if errorlevel 1 exit 1

@rem Enforce dynamic linkage
copy gettext-runtime\intl\.libs\intl.dll.lib %LIBRARY_PREFIX%\lib\intl.lib
if errorlevel 1 exit 1
