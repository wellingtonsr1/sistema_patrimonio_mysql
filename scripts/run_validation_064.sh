#!/usr/bin/env bash
#
# Validação da Feature 064 — Fluxo Global de Movimentações (Origem/Destino)
#
# Uso: bash scripts/run_validation_064.sh
#
# Pré-condição: ambiente com pytest e TestClient configurados (venv ativo ou
# equivalente). Os testes usam SQLite em memória; não depende de MariaDB.
#
# Etapas:
#  1. Teste novo isolado (esperado antes do template: US1 RED, US2 GREEN)
#  2. Régua completa da nova feature
#  3. Subconjunto de regressão (irmãs 062/063 + movimentações/busca/importação)
#  4. Régua completa do projeto (para confirmação final)
#
# Observação importante: a régua completa pode conter os mesmos 4 failures
# ambientais pré-existentes descritos no tasks.md/T001; isso não é regressão
# se forem exatamente os testes conhecidos (test_backup_config.py e
# test_migrations_052.py). Qualquer outro failure deve ser investigado.
set -euo pipefail

PY="${PYTHON:-python}"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { printf "${CYAN}[064]${NC} %s\n" "$*"; }
ok()    { printf "${GREEN}[064]${NC} %s\n" "$*"; }
warn()  { printf "${YELLOW}[064]${NC} %s\n" "$*"; }
err()   { printf "${RED}[064]${NC} %s\n" "$*"; }

check_cmd() {
  if ! command -v "$PY" >/dev/null 2>&1; then
    err "Python não encontrado. Ative o venv ou ajuste PYTHON."
    exit 1
  fi

  if ! "$PY" -m pytest --version >/dev/null 2>&1; then
    err "pytest não disponível em '$PY -m pytest'."
    exit 1
  fi
}

title() {
  printf '\n%s\n' "======================================================================"
  printf '%s\n' "$*"
  printf '%s\n\n' "======================================================================"
}

run() {
  local label="$1"
  shift
  info "$label"
  "$@"
}

 summarize_exit() {
  local label="$1"
  local rc="$2"
  if [ "$rc" -eq 0 ]; then
    ok "$label — exit 0"
  else
    warn "$label — exit $rc"
  fi
}

# ============================================================================
# 0. Pré-checks
# ============================================================================
check_cmd
info "Interpretador: $($PY --version 2>&1 || true)"
info "pytest:       $($PY -m pytest --version 2>&1 | head -1 || true)"

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# ============================================================================
# 1. Teste novo isolado
# ============================================================================
title "ETAPA 1 — Teste novo isolado (esperado: US1 RED, US2 GREEN antes do template)"

if [ -f tests/test_fluxo_global_064.py ]; then
  run "pytest tests/test_fluxo_global_064.py -v" \
    "$PY" -m pytest tests/test_fluxo_global_064.py -v
  summarize_exit "Teste novo isolado" $?
else
  err "tests/test_fluxo_global_064.py não encontrado."
  exit 1
fi

# ============================================================================
# 2. Maisリスのするため if you want to compare before/after template state,
#    rodar a ETAPA 1 antes e depois da mudança de template.
# ============================================================================
title "ETAPA 2 — Régua completa da nova feature"

run "pytest tests/test_fluxo_global_064.py -q" \
  "$PY" -m pytest tests/test_fluxo_global_064.py -q
summarize_exit "Régua da nova feature" $?

# ============================================================================
# 3. Subconjunto de regressão (irmãs 062/063 + movimentações/busca/importação)
# ============================================================================
title "ETAPA 3 — Subconjunto de regressão (sem editar testes existentes)"

REGRESSION_TESTS=(
  tests/test_movements.py
  tests/test_movements_search.py
  tests/test_import_asset_movements.py
  tests/test_departamento_destino_062.py
  tests/test_presentacao_trilha_063.py
)

missing=()
for t in "${REGRESSION_TESTS[@]}"; do
  if [ ! -f "$t" ]; then
    missing+=("$t")
  fi
done

if [ ${#missing[@]} -gt 0 ]; then
  warn "Alguns testes do subconjunto de regressão não foram encontrados:"
  for m in "${missing[@]}"; do
    warn "  - $m"
  done
  warn "Pularam-se esses arquivos no subconjunto."
fi

if [ ${#missing[@]} -lt ${#REGRESSION_TESTS[@]} ]; then
  cmd=("$PY" -m pytest --quiet)
  for t in "${REGRESSION_TESTS[@]}"; do
    if [ -f "$t" ]; then
      cmd+=("$t")
    fi
  done
  run "pytest --quiet <subconjunto>" "${cmd[@]}"
  summarize_exit "Subconjunto de regressão" $?
else
  warn "Nenhum teste do subconjunto de regressão encontrado; pular."
fi

# ============================================================================
# 4. Régua completa do projeto
# ============================================================================
title "ETAPA 4 — Régua completa do projeto"

run "pytest -q" "$PY" -m pytest -q
rc=$?
summarize_exit "Régua completa" $rc

if [ "$rc" -ne 0 ]; then
  warn "A régua completa saiu com código não-zero."
  warn "Confirme se os failures são exatamente os conhecidos (test_backup_config.py e"
  warn "test_migrations_052.py - ModuleNotFoundError dotenv/alembic em subprocesso)."
  warn "Qualquer outro failure deve ser investigado antes de considerar a feature entregue."
fi

# ============================================================================
# 5. Diferencial de produção (manualmente ou por script)
# ============================================================================
title "ETAPA 5 — Diff de produção (apenas list.html esperado)"

if command -v git >/dev/null 2>&1 && git rev-parse --git-dir >/dev/null 2>&1; then
  info "git disponível — possível verificar diff de produção."
  info "Rodar manualmente se quiser:"
  echo ""
  echo "  git diff main -- app/"
  echo ""
  echo "Esperado: apenas app/web/templates/movements/list.html"
else
  warn "git indisponível neste ambiente; diff de produção deve ser verificado manualmente."
fi

# ============================================================================
# Resumo final
# ============================================================================
title "RESUMO"
ok "Etapas executadas: 1 (teste novo) / 2 (régua nova feature) / 3 (subconjunto) / 4 (régua completa)"
info "Etapa 5 (diff de produção) é verificação manual ou via git conforme disponibilidade."
info "Validação só considera a feature pronta quando:"
info "  - testes novos (US1 + US2) estão verdes"
info "  - subconjunto de regressão não introduz failures"
info "  - régua completa não introduz regressões além dos failures ambientais conhecidos"
info "  - diff de produção mostra somente app/web/templates/movements/list.html"
