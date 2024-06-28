setlocal enableextensions

CALL win32\configure.bat --prefix=%PREFIX%
if %errorlevel% neq 0 exit /b %errorlevel%

nmake
if %errorlevel% neq 0 exit /b %errorlevel%

nmake install
if %errorlevel% neq 0 exit /b %errorlevel%

if not exist "%PREFIX%\etc" (
    mkdir "%PREFIX%\etc"
    if %errorlevel% neq 0 exit /b %errorlevel%
)

if not exist "%PREFIX%\share\rubygems" (
    mkdir "%PREFIX%\share\rubygems"
    if %errorlevel% neq 0 exit /b %errorlevel%
)

echo "gemhome: %PREFIX%/share/rubygems" > %PREFIX%/etc/gemrc
if %errorlevel% neq 0 exit /b %errorlevel%

setlocal EnableDelayedExpansion
