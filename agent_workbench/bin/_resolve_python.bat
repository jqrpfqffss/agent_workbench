@echo off
set "WB_PYTHON="
set "WB_PY_KIND="
set "WB_PY_SCORE=-1"
set "WB_PY_EXE="
set "WB_PY_DIR="

if defined AGENT_WORKBENCH_PYTHON call :consider_exe "%AGENT_WORKBENCH_PYTHON%" custom
if defined SMARTFARM_PYTHON call :consider_exe "%SMARTFARM_PYTHON%" legacy_custom

where py >nul 2>nul
if not errorlevel 1 (
  py -3 --version >nul 2>nul
  if not errorlevel 1 call :consider_command "py -3" py3
)

where python >nul 2>nul
if not errorlevel 1 call :consider_command "python" path_python

if defined LocalAppData (
  for /f "delims=" %%D in ('dir /b /ad "%LocalAppData%\Programs\Python\Python*" 2^>nul') do (
    if exist "%LocalAppData%\Programs\Python\%%D\python.exe" call :consider_exe "%LocalAppData%\Programs\Python\%%D\python.exe" local_python
  )
)

if not defined WB_PYTHON (
  echo No usable Python launcher found.
  exit /b 1
)

if /i "%WB_PY_KIND%"=="py3" (
  for /f "delims=" %%I in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do set "WB_PY_EXE=%%I"
  if defined WB_PY_EXE (
    for %%D in ("%WB_PY_EXE%") do set "WB_PY_DIR=%%~dpD"
    py -3 -c "import ssl" >nul 2>nul
    if errorlevel 1 if exist "%WB_PY_DIR%Library\bin" (
      set "PATH=%WB_PY_DIR%;%WB_PY_DIR%Library\bin;%WB_PY_DIR%DLLs;%PATH%"
    )
  )
)

exit /b 0

:consider_command
set "CANDIDATE=%~1"
set "KIND=%~2"
call %CANDIDATE% -c "import sys" >nul 2>nul
if errorlevel 1 goto :eof
set "SCORE=1"
call %CANDIDATE% -c "import yaml" >nul 2>nul
if not errorlevel 1 set "SCORE=2"
call %CANDIDATE% -c "import yaml, serial" >nul 2>nul
if not errorlevel 1 set "SCORE=3"
call :update_choice "%CANDIDATE%" "%KIND%" %SCORE%
goto :eof

:consider_exe
set "CANDIDATE=%~1"
set "KIND=%~2"
call "%CANDIDATE%" -c "import sys" >nul 2>nul
if errorlevel 1 goto :eof
set "SCORE=1"
call "%CANDIDATE%" -c "import yaml" >nul 2>nul
if not errorlevel 1 set "SCORE=2"
call "%CANDIDATE%" -c "import yaml, serial" >nul 2>nul
if not errorlevel 1 set "SCORE=3"
call :update_choice "\"%CANDIDATE%\"" "%KIND%" %SCORE%
goto :eof

:update_choice
if %3 GTR %WB_PY_SCORE% (
  set "WB_PYTHON=%~1"
  set "WB_PY_KIND=%~2"
  set "WB_PY_SCORE=%3"
)
goto :eof
