@echo off
setlocal
set SCRIPT_DIR=%~dp0
set WORKBENCH=%SCRIPT_DIR%..\workbench.py
call "%SCRIPT_DIR%_resolve_python.bat"
if errorlevel 1 exit /b 1
%WB_PYTHON% "%WORKBENCH%" %*
exit /b %ERRORLEVEL%
