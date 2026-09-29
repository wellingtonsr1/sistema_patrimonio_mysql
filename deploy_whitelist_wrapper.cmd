@echo off
REM Wrapper temporario — publica a whitelist nova (scripts/) no snapshot do PRO
call "%~dp0deploy.bat" "Deploy: publica whitelist com scripts/ no snapshot de producao"
