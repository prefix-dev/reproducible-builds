@echo on

%PYTHON% -m pip install tools/pythonpkg -vv
if %ERRORLEVEL% neq 0 exit 1

@rem Delete this file as conda-build trips over it
del test\sql\copy\csv\data\glob\crawl\.symbolic_link\mydir\link_to_upper_dir
if %ERRORLEVEL% neq 0 exit 1
