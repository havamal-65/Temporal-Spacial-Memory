@echo off
echo === Running Temporal-Spatial Knowledge Database Integration Tests ===
echo.

python standalone_test.py %*
echo.
if errorlevel 1 (
    echo Tests failed!
) else (
    echo All tests passed!
)

echo.
echo Test run complete! 