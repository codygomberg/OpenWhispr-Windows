@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo  OpenWhispr Windows -- One-Time Setup
echo ============================================================
echo.

:: Step 1: Create a virtual environment (isolated Python sandbox)
echo [1/5] Creating virtual environment...
python -m venv .venv
if errorlevel 1 (
    echo ERROR: Could not create virtual environment. Is Python installed?
    pause & exit /b 1
)

:: Step 2: Activate it
echo [2/5] Activating environment...
call .venv\Scripts\activate.bat

:: Step 3: Upgrade pip (the package installer)
echo [3/5] Upgrading pip...
python -m pip install --upgrade pip --quiet

:: Step 4: Install PyTorch with CUDA 12.4 GPU support
echo [4/5] Installing PyTorch with GPU support (this may take a few minutes)...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128 --quiet
if errorlevel 1 (
    echo ERROR: PyTorch installation failed.
    pause & exit /b 1
)

:: Step 5: Install all remaining packages
echo [5/5] Installing remaining packages...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR: Package installation failed. See above for details.
    pause & exit /b 1
)

echo.
echo ============================================================
echo  Setup complete!
echo  Double-click run.bat to launch OpenWhispr.
echo ============================================================
pause
