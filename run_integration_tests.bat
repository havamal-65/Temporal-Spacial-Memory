@echo off
echo === Running Temporal-Spatial Knowledge Database Integration Tests ===
echo.

cd tests\integration
python standalone_test.py %*

echo.
if errorlevel 1 (
    echo Tests failed!
) else (
    echo All tests passed!
)

cd ..\..
echo.
echo Test run complete! 