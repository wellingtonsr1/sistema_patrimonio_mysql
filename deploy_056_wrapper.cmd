@echo off
REM Wrapper temporario da 056 — passa a mensagem com espacos ao deploy.bat
call "%~dp0deploy.bat" "Feature 056: HTTPS nativo no uvicorn para o PWA na rede via IP"
