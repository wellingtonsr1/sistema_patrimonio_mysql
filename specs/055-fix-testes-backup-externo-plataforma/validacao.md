# Registro de Validação — Feature 055 (Constituição XII)

**Data**: 2026-09-29 · **Feature**: Correção cross-platform dos testes do destino externo (045)
**Método**: diagnóstico com tracebacks completos + prova empírica da premissa POSIX + correção confinada à infra de teste + réguas de suíte completa.

## Alteração aplicada (diff confinado — SC-003)

| Arquivo | Mudança |
|---|---|
| `tests/test_backup_externo.py` | +71/−10: helper `_bloquear_escrita(dest) -> liberar()` cross-platform + 2 pontos de uso (test F e bloco F de zero_segredos) — **zero assertions alteradas** |
| `README.md` | Nota da 045 atualizada (fim das falhas conhecidas; régua nova = 0 failed) |
| `specs/055-.../` | Artefatos spec-kit completos |

**Zero alteração** em `app/` (FR-002): o service da 045 estava correto — a etapa 6 da cópia já mapeia `PermissionError` → `REASON_SEM_PERMISSAO`.

## V1 — Diagnóstico e classificação (T001/T002) ✅

- Tracebacks: ambos os failures são `assert 'SUCCESS' == 'FAILURE'` no `external_status` — a cópia externa **succeedia** onde o teste exige falha.
- Prova empírica (Windows, 2026-09-29): `os.chmod(d, S_IRUSR|S_IXUSR)` em diretório → `os.access(d, W_OK)` ainda True e `open(d/"x.txt","w")` **cria o arquivo**. Premissa POSIX confirmada como causa raiz.
- Classificação: **premissa de teste desatualizada** — nenhum bug de produção (no Windows real, destino sem permissão é simulável por ACL; o service reage corretamente à `PermissionError`).

## V2 — Simulação cross-platform (FR-001/FR-004) ✅

- Windows: `icacls <dest> /deny *S-1-1-0:(WD)` (SID Everyone bem-conhecido — imune a locale; `WD` nega write/append data, mantendo leitura). A abertura do temporário pelo service levanta a mesma `PermissionError` mapeada → `external_status == "FAILURE"`, `external_reason == "sem permissão de escrita"`, registro FAILURE + auditoria `BACKUP_EXTERNO_FALHA` + backup local íntegro (todas as assertions originais passando).
- POSIX: ramos originais (`chmod r-x` ↔ `chmod 0o755`) preservados dentro do helper.
- Liberação em `finally` nos dois sistemas (cleanup do `tmp_path` seguro).

## V3 — Assertions intocadas (FR-003/SC-004) ✅

`git diff` do arquivo mostra apenas: imports, helper novo e a troca da mecânica de bloqueio (`chmod` → `_bloquear_escrita`/`_liberar()`) nos 2 pontos — todas as linhas de assert idênticas.

## V4 — Réguas (SC-001/SC-002/FR-005) ✅

| Régua | Resultado |
|---|---|
| `pytest tests/test_backup_externo.py` (Windows, venv) | **20 passed, 0 failed** |
| Suíte completa (venv) | **889 passed / 0 failed** em 60,7s |
| Suíte completa com `DATABASE_URL` morta (hermeticidade 054) | 887/2 → agora válida também: os 2 eram falhas de plataforma, não de conexão (caminho corrigido independe do banco) |

887 mantidos + 2 recuperados = 889. **Nenhum teste que passava passou a falhar** (verificado na suíte completa integral).

## V5 — Impacto no processo ✅

- Fim do baseline "2 failures aceitos" que regia as features 045–054: a régua de regressão das próximas features é **0 failed** (qualquer failure = regressão real).
- Alternativas rejeitadas registradas no plan (D3): probe de produção no service (desnecessário p/ os testes), monkeypatch de I/O (mascararia o caminho real), `skipif` Windows (esconderia o cenário no SO alvo).

## V6 — Limitações e decisões

- **D1**: `icacls /deny` é a simulação escolhida por ser ACL real (o mesmo mecanismo que um administrador usaria); `check=True` no deny garante que falha de simulação quebra o teste com causa visível.
- **D2**: `icacls`/SID bem-conhecido disponível em todo Windows suportado; liberação tolerante (`check=False`).
- **Limitação**: em POSIX o comportamento testado é o de `chmod`; ACLs finas (NFSv4/ACLs estendidas) seguem fora de escopo — igual à 045 original.

## Resultado

**V1–V6: PASS** — SC-001..004 satisfeitos; suíte 100% verde pela primeira vez (889/0).
