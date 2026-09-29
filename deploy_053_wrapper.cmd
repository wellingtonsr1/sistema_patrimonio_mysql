@echo off
REM Wrapper temporario da 053 — passa a mensagem com espacos ao deploy.bat
call "%~dp0deploy.bat" "Feature 053: corrige respondWith duplo no sw.js e avanca cache para v32"
