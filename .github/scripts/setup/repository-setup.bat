@echo off
setlocal enabledelayedexpansion

:: repository-setup.bat
:: Sets up a project from this harness template. Two modes, auto-detected:
::   - Activate in place: run from inside a repo already created from the
::     template (e.g. GitHub's "Use this template"). Configures the hook
::     path and runs an initial sync. No files copied.
::   - Scaffold: run pointing at an empty / non-git directory. Initializes
::     git, copies the template files, then activates as above.

echo ============================================
echo  Repository Setup - Project Template Init
echo ============================================
echo.

:: --- Resolve paths ---

:: SRC is the harness repo this script lives in (3 levels up).
pushd "%~dp0..\..\.."
set "SRC=!CD!"
popd

if "%~1"=="" (
    set "TARGET_DIR=!CD!"
) else (
    set "TARGET_DIR=%~1"
)
:: Normalize TARGET_DIR to an absolute path when it already exists.
if exist "!TARGET_DIR!\" (
    pushd "!TARGET_DIR!"
    set "TARGET_DIR=!CD!"
    popd
)

:: --- Mode detection ---

if /i "!SRC!"=="!TARGET_DIR!" goto :activate_in_place

:: --- Scaffold mode ---

echo Mode: scaffold
echo Target: !TARGET_DIR!
echo.

if exist "!TARGET_DIR!\.git" (
    echo ERROR: !TARGET_DIR! is already a git repository.
    echo        To set up a repo created from the GitHub template, run this
    echo        script from INSIDE that repo with no arguments.
    echo        Otherwise, point it at an empty or non-git directory.
    pause
    exit /b 1
)

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

echo.
echo Initializing git repository...
git init "!TARGET_DIR!"
if errorlevel 1 (
    echo ERROR: git init failed.
    pause
    exit /b 1
)

echo.
echo Copying template files from: !SRC!
echo                          to: !TARGET_DIR!
echo.

robocopy "!SRC!\.github" "!TARGET_DIR!\.github" /E /NFL /NDL /NJH /NJS
if errorlevel 8 (
    echo ERROR: Failed to copy .github directory.
    pause
    exit /b 1
)
robocopy "!SRC!\.claude\rules" "!TARGET_DIR!\.claude\rules" /E /NFL /NDL /NJH /NJS
if errorlevel 8 (
    echo ERROR: Failed to copy .claude\rules directory.
    pause
    exit /b 1
)
if not exist "!TARGET_DIR!\.claude\learning" mkdir "!TARGET_DIR!\.claude\learning"
if exist "!SRC!\.claude\learning\config.json" (
    copy /Y "!SRC!\.claude\learning\config.json" "!TARGET_DIR!\.claude\learning\config.json" >nul
    echo   .claude\learning\config.json
)
robocopy "!SRC!\docs" "!TARGET_DIR!\docs" /E /NFL /NDL /NJH /NJS
if errorlevel 8 (
    echo ERROR: Failed to copy docs directory.
    pause
    exit /b 1
)

for %%F in (CLAUDE.md .gitignore setup.bat setup.sh sync.bat) do (
    if exist "!SRC!\%%F" (
        copy /Y "!SRC!\%%F" "!TARGET_DIR!\%%F" >nul
        echo   %%F
    )
)

call :activate "!TARGET_DIR!"

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
exit /b 0

:: --- Activate in place ---

:activate_in_place
echo Mode: activate in place
echo Target: !TARGET_DIR!
echo (repository already populated -- no files copied)
call :activate "!TARGET_DIR!"

echo.
echo ============================================
echo  Activation complete: !TARGET_DIR!
echo ============================================
echo.
echo Next steps:
echo   1. Run the project-setup skill to tailor
echo      template files to your stack.
echo   2. Commit -- the pre-commit hook will run.
echo.
echo Press Enter to close.
pause >nul
exit /b 0

:: --- Shared subroutine: configure hook path + run sync ---

:activate
pushd "%~1"
if not exist ".git" (
    echo ERROR: %~1 is not a git repository. Hook installation skipped.
    popd
    pause
    exit /b 1
)
echo.
echo Configuring git hooks...
git config core.hooksPath .github/hooks
if errorlevel 1 (
    echo ERROR: Failed to configure git hooks.
    popd
    pause
    exit /b 1
)

:: Symlink into .git\hooks so clients that ignore core.hooksPath (e.g.
:: GitKraken Desktop) still pick up the pre-commit hook.
if not exist ".git\hooks" mkdir ".git\hooks"
mklink ".git\hooks\pre-commit" "..\..\.github\hooks\pre-commit" >nul 2>&1
if errorlevel 1 (
    echo WARN: Could not create symlink in .git\hooks. GitKraken may not run hooks.
    echo       Run this script as Administrator or enable Developer Mode in Windows Settings.
)
echo Git hooks installed. Pre-commit sync + validation is now active.
echo.
where python >nul 2>&1
if errorlevel 1 (
    echo WARN: python not found on PATH. Run sync.bat manually after installing Python.
) else (
    echo Running initial sync...
    python .github\scripts\sync-claude-rules.py
    if errorlevel 1 echo WARN: Sync had errors. Run sync.bat manually after fixing.
)
popd
exit /b 0
