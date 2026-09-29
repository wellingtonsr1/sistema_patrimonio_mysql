@echo off
REM Wrapper temporario da 055 — passa a mensagem com espacos ao deploy.bat
call "%~dp0deploy.bat" "Feature 055: corrige premissa POSIX nos testes de destino externo sem permissao"
