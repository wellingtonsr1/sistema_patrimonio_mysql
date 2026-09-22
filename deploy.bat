@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM  Deploy do SisPatrimonio - publicacao nos 2 GitHub
REM
REM  Uso:  deploy.bat "mensagem do commit"
REM
REM  1) commit local (se houver mudancas) na pasta de dev
REM  2) push do historico COMPLETO -> github.com/wellingtonsr1/sistema_patrimonio_mysql
REM  3) publicacao do SNAPSHOT FILTRADO (whitelist) -> github.com/wellingtonsr1/SisPatrimonioPro
REM     (repo de producao: apenas app/ data/ docs/ .gitignore README.md
REM      requirements.txt run.py seed_demo.py sistema_patrimonio.png
REM      SPEC-KIT-SISTEMA-ATUAL.md)
REM
REM  Requer: git no PATH. O branch de publicacao e sempre "main".
REM ============================================================

cd /d "%~dp0"

if "%~1"=="" (
    echo Uso: deploy.bat "mensagem do commit"
    exit /b 1
)

set PRO_REPO=git@github.com:wellingtonsr1/SisPatrimonioPro.git
set PUBLISH_BRANCH=main

REM ---------- 1) Commit na dev ----------
git status --porcelain | findstr /r /c:"." >nul 2>&1
if not errorlevel 1 (
    git add -A
    git commit -m "%~1"
    if errorlevel 1 (
        echo ERRO: falha ao commitar. Nada foi enviado.
        exit /b 1
    )
) else (
    echo [ok] Sem mudancas novas na dev.
)

REM ---------- 2) Push do historico completo (dev GitHub) ----------
echo [..] Enviando historico completo para sistema_patrimonio_mysql...
git push origin HEAD:refs/heads/main
if errorlevel 1 (
    echo ERRO: falha no push para origin. Publicacao cancelada.
    exit /b 1
)

REM ---------- 3) Snapshot filtrado para o SisPatrimonioPro ----------
echo [..] Publicando snapshot filtrado no SisPatrimonioPro...

REM 3a) arvore temporaria com o commit atual
set TMPDIR=%TEMP%\sispat_deploy_%RANDOM%
mkdir "%TMPDIR%"
git archive HEAD | tar -x -C "%TMPDIR%"
if errorlevel 1 (
    echo ERRO: falha ao extrair a arvore do commit.
    rmdir /s /q "%TMPDIR%"
    exit /b 1
)

REM 3b) whitelist: remove tudo que nao esta na lista de producao
for /d %%D in ("%TMPDIR%\*") do (
    if /i not "%%~nxD"=="app" if /i not "%%~nxD"=="data" if /i not "%%~nxD"=="docs" rmdir /s /q "%%D"
)
for %%F in ("%TMPDIR%\*") do (
    if /i not "%%~nxF"==".gitignore" if /i not "%%~nxF"=="README.md" if /i not "%%~nxF"=="requirements.txt" if /i not "%%~nxF"=="run.py" if /i not "%%~nxF"=="seed_demo.py" if /i not "%%~nxF"=="sistema_patrimonio.png" if /i not "%%~nxF"=="SPEC-KIT-SISTEMA-ATUAL.md" del /q "%%F"
)

REM 3b-2) pasta data/ (runtime) copiada do ambiente de dev
if exist "data" (
    xcopy /e /i /q /y "data" "%TMPDIR%\data\" >nul
)

REM 3c) publicacao: commit da arvore filtrada e push forcado no PRO
git -C "%TMPDIR%" init -q -b %PUBLISH_BRANCH%
git -C "%TMPDIR%" add -A
for /f %%i in ('git rev-parse --short HEAD') do set DEVHASH=%%i
git -C "%TMPDIR%" commit -q -m "%~1 (snapshot de producao de %COMPUTERNAME%, commit dev %DEVHASH%)"
if errorlevel 1 (
    echo ERRO: falha ao commitar o snapshot.
    rmdir /s /q "%TMPDIR%"
    exit /b 1
)
git -C "%TMPDIR%" log --oneline -1

echo [..] Enviando para SisPatrimonioPro...
git -C "%TMPDIR%" push -q --force "%PRO_REPO%" HEAD:refs/heads/%PUBLISH_BRANCH%
if errorlevel 1 (
    echo ERRO: falha no push para SisPatrimonioPro. O GitHub da dev ja esta atualizado.
    rmdir /s /q "%TMPDIR%"
    exit /b 1
)

REM 3e) limpeza
rmdir /s /q "%TMPDIR%"

echo.
echo [ok] Deploy concluido:
git log --oneline -1
echo      - Dev (historico completo): sistema_patrimonio_mysql  [OK]
echo      - Producao (snapshot filtrado): SisPatrimonioPro      [OK]
