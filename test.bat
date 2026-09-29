@echo off
REM ============================================================================
REM Suíte de testes do SisPatrimônio Pro — Feature 054 (runner oficial)
REM
REM SEMPRE com o Python do venv: fora dele, o subprocesso de anti-regressão
REM (test_backup_config) não encontra o dotenv do user site-packages e a
REM suíte rende um failure ambiental (D3 da validação da 053).
REM
REM Uso:
REM   test.bat                              suíte completa
REM   test.bat tests\test_inventario.py -q  arquivo específico
REM   test.bat -k hermeticidade -v          por keyword
REM ============================================================================
setlocal
set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" -m pytest %*
endlocal
