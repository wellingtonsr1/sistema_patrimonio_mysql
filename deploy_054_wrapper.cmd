@echo off
REM Wrapper temporario da 054 — passa a mensagem com espacos ao deploy.bat
call "%~dp0deploy.bat" "Feature 054: suíte de testes hermética e runner com venv"
