@echo off
setlocal
call "%~dp0agent_workbench\bin\agent_workbench.bat" %*
exit /b %ERRORLEVEL%
