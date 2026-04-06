@echo off
setlocal
call "%~dp0agent_workbench\bin\setup.bat" %*
exit /b %ERRORLEVEL%
