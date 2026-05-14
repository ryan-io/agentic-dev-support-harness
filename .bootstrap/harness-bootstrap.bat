@echo off
setlocal enabledelayedexpansion

:: llm-sw-setup.bat
:: Drop into any directory and double-click to initialize it as a new project
:: from the template repo. Sets up git, copies files, installs hooks, runs sync.

set "SRC=Z:\source\projects\claude-workflows\agentic-dev-support-harness"
set "TARGET_DIR=%CD%"

echo ============================================
echo  Quick Setup - Project Template Init
echo ============================================
echo.
echo Source:  %SRC%
echo Target:  !TARGET_DIR!
echo.

:: --- Validate ---

if not exist "%SRC%\.github" (
    echo ERROR: Template source not found at %SRC%
    goto :done
)

if exist "!TARGET_DIR!\.git" (
    echo ERROR: !TARGET_DIR! is already a git repository.
    goto :done
)

:: --- Initialize git ---

echo Initializing git repository...
git init "!TARGET_DIR!"
if errorlevel 1 (
    echo ERROR: git init failed.
    goto :done
)

:: --- Copy template files ---

echo.
echo Copying template files...

robocopy "%SRC%\.github" "!TARGET_DIR!\.github" /E /XF "*.sh" /NFL /NDL /NJH /NJS
if errorlevel 8 (
    echo ERROR: Failed to copy .github directory.
    goto :done
)
robocopy "%SRC%\.claude\rules" "!TARGET_DIR!\.claude\rules" /E /NFL /NDL /NJH /NJS
if errorlevel 8 (
    echo ERROR: Failed to copy .claude\rules directory.
    goto :done
)

:: Create learning directory and copy config
if not exist "!TARGET_DIR!\.claude\learning" mkdir "!TARGET_DIR!\.claude\learning"
if exist "%SRC%\.claude\learning\config.json" (
    copy /Y "%SRC%\.claude\learning\config.json" "!TARGET_DIR!\.claude\learning\config.json" >nul
    echo   .claude\learning\config.json
)

robocopy "%SRC%\docs" "!TARGET_DIR!\docs" /E /NFL /NDL /NJH /NJS
if errorlevel 8 (
    echo ERROR: Failed to copy docs directory.
    goto :done
)

:: Copy root files (setup shims, gitignore, hub file)
for %%F in (CLAUDE.md .gitignore setup.bat setup.sh sync.bat) do (
    if exist "%SRC%\%%F" (
        copy /Y "%SRC%\%%F" "!TARGET_DIR!\%%F" >nul
        echo   %%F
    )
)

:: --- Install hooks ---

echo.
echo Installing git hooks...
pushd "!TARGET_DIR!"
git config core.hooksPath .github/hooks
popd
echo Git hooks installed.

:: --- Initial sync ---

echo.
where python >nul 2>&1
if errorlevel 1 (
    echo WARN: Python not found on PATH. Run sync.bat manually after installing Python.
    goto :finish
)

echo Running initial sync...
pushd "!TARGET_DIR!"
python .github\scripts\sync-claude-rules.py
popd

:finish
echo.
echo ============================================
echo  Setup complete: !TARGET_DIR!
echo ============================================
echo.
echo Next steps:
echo   1. Open this directory in your editor.
echo   2. Run the project-setup skill to tailor
echo      template files to your stack.
echo   3. Make your initial commit.

:done
echo.
echo Press Enter to close.
pause >nul
