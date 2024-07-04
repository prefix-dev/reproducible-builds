@echo on

if "%ARCH%" == "32" (
  set ARCH=Win32
) else (
  set ARCH=x64
)


cd /d %SRC_DIR%\builds\msvc\vs%VS_YEAR%\
msbuild libsodium.sln /p:Configuration=DynRelease /p:Platform=%ARCH%
if errorlevel 1 exit 1
set ARTIFACTS_DIR=%SRC_DIR%\bin\%ARCH%\Release\v142

if not exist %ARTIFACTS_DIR%\dynamic\libsodium.dll    exit 1

move /y %ARTIFACTS_DIR%\dynamic\libsodium.dll %LIBRARY_BIN%
move /y  %ARTIFACTS_DIR%\dynamic\libsodium.lib %LIBRARY_LIB%
xcopy /s /y /i %SRC_DIR%\src\libsodium\include\sodium %LIBRARY_INC%\sodium
xcopy /s /y %SRC_DIR%\src\libsodium\include\sodium.h %LIBRARY_INC%\
