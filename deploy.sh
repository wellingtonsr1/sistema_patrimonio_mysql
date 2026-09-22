#!/usr/bin/env bash
# ============================================================
#  Deploy do SisPatrimônio — publicação nos 2 GitHub (Linux/macOS)
#
#  Uso:
#    ./deploy.sh "mensagem"            # publicar (commit + dev + snapshot PRO)
#    ./deploy.sh pre                   # prévia: pendentes e última publicação
#    ./deploy.sh historico [N]         # últimas N publicações no PRO (padrão 10)
#    ./deploy.sh rollback <hash>       # volta o PRO para o snapshot de <hash>
#                                      #   (hash da DEV citado na mensagem do snapshot)
#
#  Etapas da publicação:
#    1) commit local (se houver mudanças) na pasta de dev
#    2) push do histórico COMPLETO -> sistema_patrimonio_mysql
#    3) snapshot filtrado (whitelist) -> SisPatrimonioPro
#
#  Requer: git, tar. Branch de publicação: "main".
# ============================================================
set -u
cd "$(dirname "$0")" || exit 1

PRO_REPO="git@github.com:wellingtonsr1/SisPatrimonioPro.git"
DEV_REPO_NAME="sistema_patrimonio_mysql"
PUBLISH_BRANCH="main"

# ---------- UX de terminal ----------
if [ -t 1 ]; then
    C_RESET=$'\033[0m'; C_BOLD=$'\033[1m'; C_DIM=$'\033[2m'
    C_OK=$'\033[32m'; C_ERR=$'\033[31m'; C_WARN=$'\033[33m'; C_INFO=$'\033[36m'
else
    C_RESET=""; C_BOLD=""; C_DIM=""; C_OK=""; C_ERR=""; C_WARN=""; C_INFO=""
fi
step_n=0
step()  { step_n=$((step_n+1)); printf '\n%s[%d/3]%s %s\n' "$C_INFO" "$step_n" "$C_RESET" "$1"; }
ok()    { printf '  %s[OK]%s %s\n' "$C_OK" "$C_RESET" "$1"; }
info()  { printf '  %s>%s %s\n' "$C_DIM" "$C_RESET" "$1"; }
warn()  { printf '  %s[!]%s %s\n' "$C_WARN" "$C_RESET" "$1"; }
fail()  { printf '\n  %s[ERRO]%s %s\n' "$C_ERR" "$C_RESET" "$1" >&2
          [ -n "${2:-}" ] && rm -rf "$2"
          printf '\n%s✖ Deploy abortado.%s\n' "$C_ERR" "$C_RESET" >&2
          exit 1; }
banner() { printf '%s════════════════════════════════════════════════%s\n' "$C_BOLD" "$C_RESET"
          printf '%s  SisPatrimônio Pro — Deploy%s\n' "$C_BOLD" "$C_RESET"
          printf '%s════════════════════════════════════════════════%s\n\n' "$C_BOLD" "$C_RESET"; }

usage() {
    banner
    printf 'Uso:\n'
    printf '  %s./deploy.sh \"mensagem\"%s   publicar (commit + dev + snapshot PRO)\n' "$C_BOLD" "$C_RESET"
    printf '  %s./deploy.sh pre%s          prévia do que será publicado\n' "$C_BOLD" "$C_RESET"
    printf '  %s./deploy.sh historico [N]%s últimas N publicações no PRO (padrão 10)\n' "$C_BOLD" "$C_RESET"
    printf '  %s./deploy.sh rollback <hash>%s volta o PRO ao snapshot da dev <hash>\n\n' "$C_BOLD" "$C_RESET"
}

# ---------- prévia ----------
do_pre() {
    banner
    printf '%sPRÉVIA%s — estado da dev vs GitHub\n\n' "$C_BOLD" "$C_RESET"
    local pend
    pend="$(git status --porcelain)"
    if [ -n "$pend" ]; then
        printf '%sPendentes na dev (serão commitados):%s\n' "$C_WARN" "$C_RESET"
        printf '%s\n' "$pend" | sed 's/^/  /'
    else
        ok "árvore limpa — nada a commitar"
    fi
    git fetch origin main -q 2>/dev/null
    local localh remoteh
    localh="$(git rev-parse --short HEAD)"
    remoteh="$(git rev-parse --short origin/main 2>/dev/null || echo '?')"
    printf '\n  dev local  : %s\n  dev GitHub : %s\n' "$localh" "$remoteh"
    [ "$localh" = "$remoteh" ] && ok "dev sincronizada com o GitHub" || warn "dev local está à frente do GitHub (o publicar envia)"
    echo
    git fetch "$PRO_REPO" "$PUBLISH_BRANCH" -q 2>/dev/null
    local proh
    proh="$(git rev-parse --short FETCH_HEAD 2>/dev/null || echo '?')"
    printf '  PRO atual  : %s' "$proh"
    if [ "$proh" != "?" ]; then
        local devref
        devref="$(git log -1 --format=%s FETCH_HEAD 2>/dev/null | grep -o 'commit dev [0-9a-f]*' | cut -d' ' -f3 || true)"
        [ -n "$devref" ] && printf '  %s(gerado da dev %s)%s' "$C_DIM" "$devref" "$C_RESET"
    fi
    printf '\n'
    if [ -n "$(git status --porcelain)" ] || [ "$localh" != "$remoteh" ]; then
        printf '\n%s> rode: ./deploy.sh \"sua mensagem\"%s\n' "$C_BOLD" "$C_RESET"
    fi
}

# ---------- histórico ----------
do_historico() {
    local n="${1:-10}"
    banner
    printf '%sHISTÓRICO%s — últimas %s publicações no SisPatrimonioPro\n\n' "$C_BOLD" "$C_RESET" "$n"
    git fetch "$PRO_REPO" "$PUBLISH_BRANCH" -q 2>/dev/null || fail "não consegui acessar $PRO_REPO"
    git log --format='%h|%ci|%s' -"$n" FETCH_HEAD | while IFS='|' read -r h date subj; do
        local devref=""
        devref="$(printf '%s' "$subj" | grep -o 'commit dev [0-9a-f]*' | cut -d' ' -f3 || true)"
        printf '  %s%s%s  %s\n' "$C_BOLD" "$h" "$C_RESET" "${date% +0000}"
        printf '      %s\n' "$subj"
        [ -n "$devref" ] && printf '      %s↳ dev: %s%s\n' "$C_DIM" "$devref" "$C_RESET"
        echo
    done
    printf '%sDica: rollback usa o hash da DEV (↳).%s\n' "$C_DIM" "$C_RESET"
}

# ---------- rollback ----------
do_rollback() {
    local target="${1:-}"
    [ -z "$target" ] && usage && fail "rollback exige o hash da DEV (veja ./deploy.sh historico)"
    banner
    printf '%sROLLBACK%s — restaurando o PRO para o snapshot da dev %s%s%s\n\n' "$C_BOLD" "$C_RESET" "$C_BOLD" "$target" "$C_RESET"
    git cat-file -e "$target^{commit}" 2>/dev/null || fail "hash $target não existe na dev local."
    step "Gerando o snapshot da dev $target (mesma whitelist)"
    local TMPDIR
    TMPDIR="$(mktemp -d "${TMPDIR:-/tmp}/sispat_rb_XXXXXX")" || fail "sem diretório temporário."
    git archive "$target" | tar -x -C "$TMPDIR" || fail "falha ao extrair a árvore." "$TMPDIR"
    find "$TMPDIR" -mindepth 1 -maxdepth 1 \
        ! -name app ! -name data ! -name docs \
        ! -name .gitignore ! -name README.md ! -name requirements.txt \
        ! -name run.py ! -name seed_demo.py ! -name sistema_patrimonio.png \
        ! -name SPEC-KIT-SISTEMA-ATUAL.md \
        -exec rm -rf {} +
    find "$TMPDIR/docs" -mindepth 1 -maxdepth 1 \
        \( -name "doc_provi"* -o ! -name "*.md" \) \
        -exec rm -rf {} + 2>/dev/null || true
    mkdir -p "$TMPDIR/data/backups" "$TMPDIR/data/logs"
    touch "$TMPDIR/data/backups/.gitkeep" "$TMPDIR/data/logs/.gitkeep"
    ok "árvore filtrada pronta"
    step "Publicando rollback no SisPatrimonioPro"
    git -C "$TMPDIR" init -q -b "$PUBLISH_BRANCH"
    git -C "$TMPDIR" add -A
    git -C "$TMPDIR" add -f data 2>/dev/null || true
    git -C "$TMPDIR" commit -q -m "ROLLBACK para a dev $target (publicado de $(hostname))"
    git -C "$TMPDIR" log --oneline -1
    git -C "$TMPDIR" push -q --force "$PRO_REPO" "HEAD:refs/heads/$PUBLISH_BRANCH" \
        || fail "falha no push do rollback." "$TMPDIR"
    ok "PRO restaurado para o conteúdo da dev $target"
    rm -rf "$TMPDIR"
    printf '\n%s✔ Rollback concluído.%s Na produção: %sgit pull%s e reinicie o serviço.\n' "$C_OK" "$C_RESET" "$C_BOLD" "$C_RESET"
}

# ---------- publicar ----------
do_publicar() {
    local MSG="$1"
    banner
    step "Commit na dev"
    if [ -n "$(git status --porcelain)" ]; then
        git add -A || fail "falha ao adicionar arquivos."
        git commit -m "$MSG" || fail "falha ao commitar. Nada foi enviado."
        ok "commit criado: $(git rev-parse --short HEAD)"
    else
        warn "sem mudanças novas na dev (seguindo para publicar)"
    fi
    step "Enviando histórico completo para $DEV_REPO_NAME"
    git push origin HEAD:refs/heads/main || fail "falha no push para origin. Publicação cancelada."
    ok "dev atualizada no GitHub ($(git rev-parse --short HEAD))"
    step "Publicando snapshot filtrado no SisPatrimonioPro"
    local TMPDIR
    TMPDIR="$(mktemp -d "${TMPDIR:-/tmp}/sispat_deploy_XXXXXX")" || fail "sem diretório temporário."
    git archive HEAD | tar -x -C "$TMPDIR" || fail "falha ao extrair a árvore do commit." "$TMPDIR"
    find "$TMPDIR" -mindepth 1 -maxdepth 1 \
        ! -name app ! -name data ! -name docs \
        ! -name .gitignore ! -name README.md ! -name requirements.txt \
        ! -name run.py ! -name seed_demo.py ! -name sistema_patrimonio.png \
        ! -name SPEC-KIT-SISTEMA-ATUAL.md \
        -exec rm -rf {} +
    find "$TMPDIR/docs" -mindepth 1 -maxdepth 1 \
        \( -name "doc_provi"* -o ! -name "*.md" \) \
        -exec rm -rf {} + 2>/dev/null || true
    mkdir -p "$TMPDIR/data/backups" "$TMPDIR/data/logs"
    touch "$TMPDIR/data/backups/.gitkeep" "$TMPDIR/data/logs/.gitkeep"
    git -C "$TMPDIR" init -q -b "$PUBLISH_BRANCH"
    git -C "$TMPDIR" add -A
    git -C "$TMPDIR" add -f data 2>/dev/null || true
    local DEVHASH
    DEVHASH="$(git rev-parse --short HEAD)"
    git -C "$TMPDIR" commit -q -m "$MSG (snapshot de produção de $(hostname), commit dev $DEVHASH)" \
        || fail "falha ao commitar o snapshot." "$TMPDIR"
    ok "snapshot pronto ($TMPDIR → 1 commit)"
    git -C "$TMPDIR" push -q --force "$PRO_REPO" "HEAD:refs/heads/$PUBLISH_BRANCH" \
        || fail "falha no push para SisPatrimonioPro. O GitHub da dev já está atualizado." "$TMPDIR"
    ok "PRO publicado: $(git -C "$TMPDIR" log --oneline -1 | cut -c1-60)…"
    rm -rf "$TMPDIR"
    printf '\n%s════════════════════════════════════════════════%s\n' "$C_BOLD" "$C_RESET"
    printf '%s✔ Deploy concluído%s — dev %s · PRO %s\n' "$C_OK" "$C_RESET" "$DEVHASH" "$(git rev-parse --short FETCH_HEAD 2>/dev/null || echo '?')"
    printf '%s════════════════════════════════════════════════%s\n' "$C_BOLD" "$C_RESET"
}

# ---------- roteamento ----------
case "${1:-}" in
    pre)        do_pre ;;
    historico)  do_historico "${2:-10}" ;;
    rollback)   shift; do_rollback "${1:-}" ;;
    ""|-h|--help|help) usage ;;
    *)          do_publicar "$1" ;;
esac
