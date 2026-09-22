@echo off
for /f %%i in ('git status --porcelain ^| find /c /v ""') do set PEND=%%i
echo PEND=[%PEND%]
echo FIM
