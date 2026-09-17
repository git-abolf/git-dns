@echo off
setlocal
cd /d %~dp0
py -3 -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements\windows.txt
python -m PyInstaller DNSMasterPro.spec --clean --noconfirm
if errorlevel 1 exit /b 1
echo Build complete: dist\DNSMasterPro\DNSMasterPro.exe
