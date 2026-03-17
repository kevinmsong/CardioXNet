@echo off
setlocal
cd /d "%~dp0"

echo [1/3] Building React frontend...
cd frontend
call npm install --silent
call npm run build
cd ..
if not exist "frontend\dist\index.html" (
    echo ERROR: Frontend build failed.
    pause & exit /b 1
)
echo     Done.

echo [2/3] Running PyInstaller...
pyinstaller cardioxnet.spec --clean --noconfirm
if not exist "dist\CardioXNet.exe" (
    echo ERROR: PyInstaller failed.
    pause & exit /b 1
)
echo     Done.

echo [3/3] Build complete!
echo.
echo  Output: dist\CardioXNet.exe
echo  Double-click it to launch CardioXNet.
echo.
pause
