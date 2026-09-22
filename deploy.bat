@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM  Deploy do SisPatrimonio - publicacao nos 2 GitHub (Windows)
REM
REM  Uso:
REM    deploy.bat "mensagem"            publicar (commit + dev + snapshot PRO)
REM    deploy.bat pre                   pre-via: pendentes e ultima publicacao
REM    deploy.bat historico [N]         ultimas N publicacoes no PRO (padrao 10)
REM    deploy.bat rollback <hash>       volta o PRO para o snapshot de <hash>
REM                                     (hash da DEV citado na mensagem do snapshot)
REM
REM  Etapas da publicacao:
REM    1) commit local (se houver mudancas) na pasta de dev
REM    2) push do historico COMPLETO -> sistema_patrimonio_mysql
REM    3) snapshot filtrado (whitelist) -> SisPatrimonioPro
REM
REM  Requer: git no PATH. Branch de publicacao: "main".
REM ============================================================

cd /d "%~dp0"

set PRO_REPO=git@github.com:wellingtonsr1/SisPatrimonioPro.git
set DEV_REPO_NAME=sistema_patrimonio_mysql
set PUBLISH_BRANCH=main

REM ---------- UX de terminal ----------
REM ANSI em Win10+: ativa via variavel de registro no inicio da sessao do cmd
set ESC=
for /f %%e in ('echo prompt $E ^| cmd') do set ESC=%%e
set C_RESET=%ESC%[0m
set C_BOLD=%ESC%[1m
set C_DIM=%ESC%[2m
set C_OK=%ESC%[32m
set C_ERR=%ESC%[31m
set C_WARN=%ESC%[33m
set C_INFO=%ESC%[36m

banner
if "%~1"=="" goto :usage
if /i "%~1"=="pre"       goto :pre
if /i "%~1"=="historico" goto :historico
if /i "%~1"=="rollback"  goto :rollback
if /i "%~1"=="-h"        goto :usage
if /i "%~1"=="--help"    goto :usage
if /i "%~1"=="help"      goto :usage
goto :publicar

:usage
echo Uso:
echo   deploy.bat "mensagem"        publicar (commit + dev + snapshot PRO)
echo   deploy.bat pre               pre-via do que sera publicado
echo   deploy.bat historico [N]     ultimas N publicacoes no PRO (padrao 10)
echo   deploy.bat rollback ^<hash^>  volta o PRO ao snapshot da dev ^<hash^>
exit /b 1

REM ============================================================
:pre
echo %C_BOLD%PRE-VIA%C_RESET% - estado da dev vs GitHub
echo.
git status --porcelain | findstr /r /c:"." >"%TEMP%\_sispat_pend.txt" 2>nul
set PEND=0
for /f %%i in ('%SystemRoot%\System32\find.exe /c /v "" ^< "%TEMP%\_sispat_pend.txt"') do set PEND=%%i
if %PEND% GTR 0 (
    echo %C_WARN%[ATENCAO]%C_RESET% Pendentes na dev %C_DIM%- serao commitados no publicar%C_RESET%:
    git status --porcelain
) else (
    call :ok "arvore limpa - nada a commitar"
)
del "%TEMP%\_sispat_pend.txt" 2>nul
git fetch origin main -q 2>nul
for /f %%i in ('git rev-parse --short HEAD') do set LOCALH=%%i
for /f %%i in ('git rev-parse --short origin/main 2^>nul') do set REMOTEH=%%i
if "%REMOTEH%"=="" set REMOTEH=?
echo.
echo   dev local  : %LOCALH%
echo   dev GitHub : %REMOTEH%
if "%LOCALH%"=="%REMOTEH%" (call :ok "dev sincronizada com o GitHub") else (call :warn "dev local a frente do GitHub (o publicar envia)")
git fetch "%PRO_REPO%" %PUBLISH_BRANCH% -q 2>nul
set PROH=?
for /f %%i in ('git rev-parse --short FETCH_HEAD 2^>nul') do set PROH=%%i
echo   PRO atual  : %PROH%
echo.
echo %C_BOLD%^> rode: deploy.bat "sua mensagem"%C_RESET%
goto :eof

REM ============================================================
:historico
set N=%~2
if "%N%"=="" set N=10
echo %C_BOLD%HISTORICO%C_RESET% - ultimas %N% publicacoes no SisPatrimonioPro
echo.
git fetch "%PRO_REPO%" %PUBLISH_BRANCH% -q 2>nul
if errorlevel 1 (
    call :err "nao consegui acessar o repositorio do PRO"
    exit /b 1
)
for /f "usebackq delims=" %%L in (`git log --format^="%%h^^^|%%ci^^^|%%s" -%N% FETCH_HEAD`) do (
    set "LINE=%%L"
    set "H=!LINE:%%|=%%"
    echo   !LINE!
    echo.
)
echo %C_DIM%Dica: rollback usa o hash da DEV citado na mensagem.%C_RESET%
goto :eof

REM ============================================================
:rollback
set TARGET=%~2
if "%TARGET%"=="" goto :usage
echo %C_BOLD%ROLLBACK%C_RESET% - restaurando o PRO para o snapshot da dev %C_BOLD%%TARGET%%C_RESET%
echo.
git cat-file -e "%TARGET%^{commit}" 2>nul
if errorlevel 1 (
    call :err "hash %TARGET% nao existe na dev local."
    exit /b 1
)
set step_n=0

echo %C_INFO%[1/2]%C_RESET% Gerando o snapshot da dev %TARGET% (mesma whitelist)
set "TMPDIR=%TEMP%\sispat_rb_%RANDOM%"
mkdir "%TMPDIR%"
git archive %TARGET% | tar -x -C "%TMPDIR%"
if errorlevel 1 call :fail2 "falha ao extrair a arvore." "%TMPDIR%"
for /d %%D in ("%TMPDIR%\*") do (
    if /i not "%%~nxD"=="app" if /i not "%%~nxD"=="data" if /i not "%%~nxD"=="docs" rmdir /s /q "%%D"
)
for %%F in ("%TMPDIR%\*") do (
    if /i not "%%~nxF"==".gitignore" if /i not "%%~nxF"=="README.md" if /i not "%%~nxF"=="requirements.txt" if /i not "%%~nxF"=="run.py" if /i not "%%~nxF"=="seed_demo.py" if /i not "%%~nxF"=="sistema_patrimonio.png" if /i not "%%~nxF"=="SPEC-KIT-SISTEMA-ATUAL.md" del /q "%%F"
)
for /d %%D in ("%TMPDIR%\docs\*") do (
    set "N=%%~nxD"
    echo !N! | findstr /i /b "doc_provi" >nul 2>&1 && rmdir /s /q "%%D"
)
for %%F in ("%TMPDIR%\docs\*") do (
    set "F=%%~nxF"
    echo !F! | findstr /i ".md" >nul 2>&1 || del /q "%%F" 2>nul
)
if not exist "%TMPDIR%\data\backups" mkdir "%TMPDIR%\data\backups"
if not exist "%TMPDIR%\data\logs" mkdir "%TMPDIR%\data\logs"
type nul > "%TMPDIR%\data\backups\.gitkeep"
type nul > "%TMPDIR%\data\logs\.gitkeep"
call :ok "arvore filtrada pronta"

echo %C_INFO%[2/2]%C_RESET% Publicando rollback no SisPatrimonioPro
git -C "%TMPDIR%" init -q -b %PUBLISH_BRANCH%
git -C "%TMPDIR%" add -A
git -C "%TMPDIR%" add -f data 2>nul
git -C "%TMPDIR%" commit -q -m "ROLLBACK para a dev %TARGET% (publicado de %COMPUTERNAME%)"
if errorlevel 1 call :fail2 "falha ao commitar o rollback." "%TMPDIR%"
git -C "%TMPDIR%" log --oneline -1
git -C "%TMPDIR%" push -q --force "%PRO_REPO%" HEAD:refs/heads/%PUBLISH_BRANCH%
if errorlevel 1 call :fail2 "falha no push do rollback." "%TMPDIR%"
call :ok "PRO restaurado para o conteudo da dev %TARGET%"
rmdir /s /q "%TMPDIR%"
echo.
echo %C_OK%[OK]%C_RESET% Rollback concluido. Na producao: %C_BOLD%git pull%C_RESET% e reinicie o servico.
goto :eof

REM ============================================================
:publicar
set MSG=%~1

set step_n=0
echo %C_INFO%[1/3]%C_RESET% Commit na dev
git status --porcelain | findstr /r /c:"." >nul 2>&1
if not errorlevel 1 (
    git add -A
    if errorlevel 1 call :fail "falha ao adicionar arquivos."
    git commit -m "%MSG%"
    if errorlevel 1 call :fail "falha ao commitar. Nada foi enviado."
    for /f %%i in ('git rev-parse --short HEAD') do call :ok "commit criado: %%i"
) else (
    call :warn "sem mudancas novas na dev (seguindo para publicar)"
)

echo %C_INFO%[2/3]%C_RESET% Enviando historico completo para %DEV_REPO_NAME%
git push origin HEAD:refs/heads/main
if errorlevel 1 call :fail "falha no push para origin. Publicacao cancelada."
for /f %%i in ('git rev-parse --short HEAD') do call :ok "dev atualizada no GitHub (%%i)"

echo %C_INFO%[3/3]%C_RESET% Publicando snapshot filtrado no SisPatrimonioPro
set "TMPDIR=%TEMP%\sispat_deploy_%RANDOM%"
mkdir "%TMPDIR%"
git archive HEAD | tar -x -C "%TMPDIR%"
if errorlevel 1 call :fail2 "falha ao extrair a arvore do commit." "%TMPDIR%"
for /d %%D in ("%TMPDIR%\*") do (
    if /i not "%%~nxD"=="app" if /i not "%%~nxD"=="data" if /i not "%%~nxD"=="docs" rmdir /s /q "%%D"
)
for %%F in ("%TMPDIR%\*") do (
    if /i not "%%~nxF"==".gitignore" if /i not "%%~nxF"=="README.md" if /i not "%%~nxF"=="requirements.txt" if /i not "%%~nxF"=="run.py" if /i not "%%~nxF"=="seed_demo.py" if /i not "%%~nxF"=="sistema_patrimonio.png" if /i not "%%~nxF"=="SPEC-KIT-SISTEMA-ATUAL.md" del /q "%%F"
)
for /d %%D in ("%TMPDIR%\docs\*") do (
    set "N=%%~nxD"
    echo !N! | findstr /i /b "doc_provi" >nul 2>&1 && rmdir /s /q "%%D"
)
for %%F in ("%TMPDIR%\docs\*") do (
    set "F=%%~nxF"
    echo !F! | findstr /i ".md" >nul 2>&1 || del /q "%%F" 2>nul
)
if not exist "%TMPDIR%\data\backups" mkdir "%TMPDIR%\data\backups"
if not exist "%TMPDIR%\data\logs" mkdir "%TMPDIR%\data\logs"
type nul > "%TMPDIR%\data\backups\.gitkeep"
type nul > "%TMPDIR%\data\logs\.gitkeep"
git -C "%TMPDIR%" init -q -b %PUBLISH_BRANCH%
git -C "%TMPDIR%" add -A
git -C "%TMPDIR%" add -f data 2>nul
for /f %%i in ('git rev-parse --short HEAD') do set DEVHASH=%%i
git -C "%TMPDIR%" commit -q -m "%MSG% (snapshot de producao de %COMPUTERNAME%, commit dev %DEVHASH%)"
if errorlevel 1 call :fail2 "falha ao commitar o snapshot." "%TMPDIR%"
call :ok "snapshot pronto (1 commit)"
git -C "%TMPDIR%" push -q --force "%PRO_REPO%" HEAD:refs/heads/%PUBLISH_BRANCH%
if errorlevel 1 call :fail2 "falha no push para SisPatrimonioPro. O GitHub da dev ja esta atualizado." "%TMPDIR%"
call :ok "PRO publicado"
rmdir /s /q "%TMPDIR%"

echo.
echo %C_BOLD%================================================%C_RESET%
echo %C_OK%[OK]%C_RESET% Deploy concluido - dev %DEVHASH% publicado no PRO
echo %C_BOLD%================================================%C_RESET%
goto :eof

REM ---------- helpers ----------
:ok
echo   %C_OK%[OK]%C_RESET% %~1
goto :eof
:warn
echo   %C_WARN%[!]%C_RESET% %~1
goto :eof
:err
echo   %C_ERR%[ERRO]%C_RESET% %~1
goto :eof
:fail
echo   %C_ERR%[ERRO]%C_RESET% %~1
echo.
echo %C_ERR%x Deploy abortado.%C_RESET%
exit /b 1
:fail2
echo   %C_ERR%[ERRO]%C_RESET% %~1
rmdir /s /q "%~2" 2>nul
echo.
echo %C_ERR%x Deploy abortado.%C_RESET%
exit /b 1
:banner
echo %C_BOLD%================================================%C_RESET%
echo %C_BOLD%  SisPatrimonio Pro - Deploy%C_RESET%
echo %C_BOLD%================================================%C_RESET%
goto :eof
