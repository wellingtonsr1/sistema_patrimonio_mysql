#!/usr/bin/env bash
# ============================================================
#  Deploy do SisPatrimonio - publicacao nos 2 GitHub (Linux/macOS)
#
#  Uso:  ./deploy.sh "mensagem do commit"
#
#  1) commit local (se houver mudancas) na pasta de dev
#  2) push do historico COMPLETO -> github.com/wellingtonsr1/sistema_patrimonio_mysql
#  3) publicacao do SNAPSHOT FILTRADO (whitelist) -> github.com/wellingtonsr1/SisPatrimonioPro
#     (repo de producao: apenas app/ data/ docs/ .gitignore README.md
#      requirements.txt run.py seed_demo.py sistema_patrimonio.png
#      SPEC-KIT-SISTEMA-ATUAL.md)
#
#  Requer: git, tar. O branch de publicacao e sempre "main".
# ============================================================
set -u

cd "$(dirname "$0")" || exit 1

if [ $# -lt 1 ] || [ -z "$1" ]; then
    echo 'Uso: ./deploy.sh "mensagem do commit"'
    exit 1
fi
MSG="$1"

PRO_REPO="git@github.com:wellingtonsr1/SisPatrimonioPro.git"
PUBLISH_BRANCH="main"

fail() {
    echo "ERRO: $1" >&2
    [ -n "${2:-}" ] && rm -rf "$2"
    exit 1
}

# ---------- 1) Commit na dev ----------
if [ -n "$(git status --porcelain)" ]; then
    git add -A || fail "falha ao adicionar arquivos."
    git commit -m "$MSG" || fail "falha ao commitar. Nada foi enviado."
else
    echo "[ok] Sem mudancas novas na dev."
fi

# ---------- 2) Push do historico completo (dev GitHub) ----------
echo "[..] Enviando historico completo para sistema_patrimonio_mysql..."
git push origin HEAD:refs/heads/main || fail "falha no push para origin. Publicacao cancelada."

# ---------- 3) Snapshot filtrado para o SisPatrimonioPro ----------
echo "[..] Publicando snapshot filtrado no SisPatrimonioPro..."

# 3a) arvore temporaria com o commit atual
TMPDIR="$(mktemp -d "${TMPDIR:-/tmp}/sispat_deploy_XXXXXX")" || fail "falha ao criar diretorio temporario."
git archive HEAD | tar -x -C "$TMPDIR" || fail "falha ao extrair a arvore do commit." "$TMPDIR"

# 3b) whitelist: remove tudo que nao esta na lista de producao
find "$TMPDIR" -mindepth 1 -maxdepth 1 \
    ! -name app ! -name data ! -name docs \
    ! -name .gitignore ! -name README.md ! -name requirements.txt \
    ! -name run.py ! -name seed_demo.py ! -name sistema_patrimonio.png \
    ! -name SPEC-KIT-SISTEMA-ATUAL.md \
    -exec rm -rf {} +

# 3b-1) dentro de docs/, exclui a pasta de documentos provisórios (doc_provi*)
# e qualquer não-.md (ex.: "nome a conferir.txt")
find "$TMPDIR/docs" -mindepth 1 -maxdepth 1 \
    ! -name 'doc_provi*' ! -name '*.md' \
    -exec rm -rf {} + 2>/dev/null || true

# 3b-2) data/: apenas a estrutura de pastas (backups/logs vazios).
# Patrimonio.db (legado SQLite) e logs NAO entram no snapshot.
# .gitkeep mantem as pastas vazias visiveis no git.
mkdir -p "$TMPDIR/data/backups" "$TMPDIR/data/logs"
touch "$TMPDIR/data/backups/.gitkeep" "$TMPDIR/data/logs/.gitkeep"

# 3c) publicacao: commit da arvore filtrada e push forcado no PRO
git -C "$TMPDIR" init -q -b "$PUBLISH_BRANCH" || fail "falha ao init do snapshot." "$TMPDIR"
# data/ e runtime gitignored na dev - aqui entra de proposito no snapshot
git -C "$TMPDIR" add -A
git -C "$TMPDIR" add -f data 2>/dev/null || true
DEVHASH="$(git rev-parse --short HEAD)"
git -C "$TMPDIR" commit -q -m "$MSG (snapshot de producao de $(hostname), commit dev $DEVHASH)" \
    || fail "falha ao commitar o snapshot." "$TMPDIR"
git -C "$TMPDIR" log --oneline -1

echo "[..] Enviando para SisPatrimonioPro..."
git -C "$TMPDIR" push -q --force "$PRO_REPO" "HEAD:refs/heads/$PUBLISH_BRANCH" \
    || fail "falha no push para SisPatrimonioPro. O GitHub da dev ja esta atualizado." "$TMPDIR"

# 3d) limpeza
rm -rf "$TMPDIR"

echo ""
echo "[ok] Deploy concluido:"
git log --oneline -1
echo "     - Dev (historico completo): sistema_patrimonio_mysql  [OK]"
echo "     - Producao (snapshot filtrado): SisPatrimonioPro      [OK]"
