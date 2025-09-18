:: BatchGotAdmin
:-------------------------------------
REM  --> Check for permissions
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"

REM --> If error flag set, we do not have admin.
if '%errorlevel%' NEQ '0' (
    echo Requesting administrative privileges...
    goto UACPrompt
) else ( goto gotAdmin )

:UACPrompt
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    echo UAC.ShellExecute "%~s0", "", "", "runas", 1 >> "%temp%\getadmin.vbs"

    "%temp%\getadmin.vbs"
    exit /B

:gotAdmin
    if exist "%temp%\getadmin.vbs" ( del "%temp%\getadmin.vbs" )
    pushd "%CD%"
    CD /D "%~dp0"

:: Script to Launch Migration from ChatGPT to LM Studio
@echo off
:: mode con: cols=160 lines=50

echo Initiating Migration Tools

echo Detecting Python 3.12.2 installation...
IF not exist "%LOCALAPPDATA%\Programs\Python\Python312" (GOTO setup_python)
echo Python 3.12.2 Detected! Proceeding...
GOTO :setup_venv

:setup_python
echo Installing Python 3.12.2(x64) ...
"%~dp0/Software_WIN/python-3.12.2-amd64.exe" /quiet PrependPath=1 Include_test=0 SimpleInstall=1
echo Installed Python!
GOTO :setup_venv

:setup_venv
IF exist "%~dp0\venv" (GOTO migration_launch_script)
"%LOCALAPPDATA%\Programs\Python\Python312\python" -m venv "%~dp0\venv"
GOTO :migration_launch_script


:migration_launch_script
call "%~dp0\venv\Scripts\activate"
"%~dp0\venv\Scripts\python" -m pip install -r "%~dp0\Python\requirements.txt"
echo Executing Migration Script...
"%~dp0\venv\Scripts\python" "%~dp0\Python\conversation_symbolic_field_analyzer.py" --clean
pause