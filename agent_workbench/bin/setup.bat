@echo off
setlocal
set SCRIPT_DIR=%~dp0
set ROOT=%SCRIPT_DIR%..
call "%SCRIPT_DIR%_resolve_python.bat"
if errorlevel 1 (
  echo Failed to resolve Python launcher.
  exit /b 1
)

%WB_PYTHON% -c "import yaml, serial" >nul 2>nul
if errorlevel 1 (
  %WB_PYTHON% -m pip --version >nul 2>nul
  if errorlevel 1 (
    echo pip not found for [%WB_PYTHON%], trying ensurepip...
    %WB_PYTHON% -m ensurepip --upgrade >nul 2>nul
  )

  %WB_PYTHON% -m pip --version >nul 2>nul
  if errorlevel 1 (
    echo Failed to initialize pip for [%WB_PYTHON%].
    exit /b 1
  )

  %WB_PYTHON% -m pip install --disable-pip-version-check -r "%ROOT%\requirements.txt"
  if errorlevel 1 (
    echo Failed to install Python dependencies.
    exit /b 1
  )
)

call "%SCRIPT_DIR%agent_workbench.bat" doctor
if errorlevel 1 exit /b %ERRORLEVEL%
call "%SCRIPT_DIR%agent_workbench.bat" init-vscode
exit /b %ERRORLEVEL%
