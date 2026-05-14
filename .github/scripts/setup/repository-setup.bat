@echo off
setlocal enabledelayedexpansion

:: repository-setup.bat
:: Initializes a new git repository and copies all template files into it.
:: Run this first, then use the project-setup skill to tailor the markdown files.

echo ============================================
echo  Repository Setup - Project Template Init
echo ============================================
echo.

:: --- Step 1: Get target directory (default: current directory) ---

if "%~1"=="" (
    set "TARGET_DIR=%CD%"
    echo No path provided - using current directory.
) else (
    set "TARGET_DIR=%~1"
)

:: --- Step 2: Validate target ---

echo Target: !TARGET_DIR!
echo.

if exist "!TARGET_DIR!\.git" (
    echo ERROR: !TARGET_DIR! is already a git repository.
    echo        Use an empty or non-git directory.
    pause
    exit /b 1
)

:: --- Step 3: Create target directory if needed ---

if not exist "!TARGET_DIR!" (
    mkdir "!TARGET_DIR!"
    if errorlevel 1 (
        echo ERROR: Could not create directory: !TARGET_DIR!
        pause
        exit /b 1
    )
    echo Created: !TARGET_DIR!
) else (
    echo Using existing directory: !TARGET_DIR!
)

:: --- Step 4: Initialize git repository ---

echo.
echo Initializing git repository...
git init "!TARGET_DIR!"
if errorlevel 1 (
    echo ERROR: git init failed.
    pause
    exit /b 1
)

:: --- Step 5: Copy template files ---

set "SRC=%~dp0..\..\..\"
echo.
echo Copying template files from: %SRC%
echo                          to: !TARGET_DIR!
echo.

:: Use robocopy to mirror directory structure.
:: /E   = include subdirectories (even empty ones)
:: /XD  = exclude directories
:: /XF  = exclude files
:: /NFL /NDL /NJH /NJS = reduce noise in output
:: Robocopy exit codes: 0-7 = success, >=8 = failure
robocopy "%SRC%.github" "!TARGET_DIR!\.github" /E /XF "*.sh" /NFL /NDL /NJH /NJS
if errorlevel 8 (
    echo ERROR: Failed to copy .github directory.
    pause
    exit /b 1
)
robocopy "%SRC%.claude\rules" "!TARGET_DIR!\.claude\rules" /E /NFL /NDL /NJH /NJS
if errorlevel 8 (
    echo ERROR: Failed to copy .claude\rules directory.
    pause
    exit /b 1
)
if not exist "!TARGET_DIR!\.claude\learning" mkdir "!TARGET_DIR!\.claude\learning"
if exist "%SRC%.claude\learning\config.json" (
    copy /Y "%SRC%.claude\learning\config.json" "!TARGET_DIR!\.claude\learning\config.json" >nul
    echo   .claude\learning\config.json
)
robocopy "%SRC%docs" "!TARGET_DIR!\docs" /E /NFL /NDL /NJH /NJS
if errorlevel 8 (
    echo ERROR: Failed to copy docs directory.
    pause
    exit /b 1
)

:: Copy root files individually (exclude this script and git artifacts)
for %%F in (CLAUDE.md .gitignore setup.bat setup.sh sync.bat) do (
    if exist "%SRC%%%F" (
        copy /Y "%SRC%%%F" "!TARGET_DIR!\%%F" >nul
        echo   %%F
    )
)

:: --- Step 6: Install git hooks ---

echo.
echo Installing git hooks...
pushd "!TARGET_DIR!"
if not exist ".git" (
    echo ERROR: !TARGET_DIR! is not a git repository. Hook installation skipped.
    popd
    pause
    exit /b 1
)
git config core.hooksPath .github/hooks
if errorlevel 1 (
    echo ERROR: Failed to configure git hooks.
    popd
    pause
    exit /b 1
)
popd
echo Git hooks installed. Pre-commit sync is now active.

:: --- Step 8: Run initial sync ---

echo.
echo Running initial sync...
pushd "!TARGET_DIR!"
where python >nul 2>&1
if errorlevel 1 (
    echo WARN: python not found on PATH. Run sync.bat manually after installing Python.
) else (
    python .github\scripts\sync-claude-rules.py
)
if errorlevel 1 (
    echo.
    echo WARN: Sync had errors. Run sync.bat manually after fixing.
)
popd

:: --- Done ---

echo.
echo ============================================
echo  Setup complete: !TARGET_DIR!
echo ============================================
echo.
echo Next steps:
echo   1. Open the repository in your editor.
echo   2. Run the project-setup skill to tailor
echo      template files to your stack.
echo   3. Make your initial commit.
echo.
echo Press Enter to close.
pause >nul
