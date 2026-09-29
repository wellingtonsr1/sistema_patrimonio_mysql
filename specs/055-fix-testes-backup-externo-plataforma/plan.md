# Implementation Plan: Correção cross-platform dos testes do destino externo (055)

**Branch**: `055-fix-testes-backup-externo-plataforma` · **Spec**: [spec.md](spec.md) · **Created**: 2026-09-29

## Summary

Substituir a premissa POSIX (`os.chmod r-x` no diretório) por simulação cross-platform de "sem permissão": no Windows, ACL real via `icacls /deny *S-1-1-0:(WD)` no diretório de destino, que faz a etapa 6 da cópia (`open(tmp,"wb")`) levantar exatamente a `PermissionError` que o service mapeia para `REASON_SEM_PERMISSAO`. Produção intocada; assertions intocadas.

## Technical Context

**Arquivo único**: `tests/test_backup_externo.py`. **Diagnóstico**: 2 failures (F/G) desde a 045; prova empírica de que `chmod r-x` + criação de arquivo funciona no Windows; service examinado (mapeamento `PermissionError` → reason correto). O `test_zero_segredos_em_logs` falha apenas porque executa o cenário F embutido — uma única correção atinge os dois.

## Constitution Check

| Princípio | Status | Nota |
|---|---|---|
| I. Evolução incremental | PASS | Só infra de teste |
| II. Arquitetura em camadas | PASS | Intocada |
| III. Regras de negócio | PASS | Zero regra tocada |
| IV/V. Integridade patrimonial | PASS | Intocada |
| VI. Segurança RBAC | PASS | Intocada |
| VII. Banco protegido | PASS | Zero DDL/produção |
| VIII. Testes como não-regressão | PASS | Suíte passa a 0 failed (régua mais forte) |
| IX. Auditoria | PASS | Assertions de auditoria intactas |
| XI. Documentação fiel | PASS | README nota 045 atualizada (fim das falhas conhecidas) |
| XII. Especificações e validação | PASS | validacao.md |

**GATE: PASS 10/10**

## Design

### D1 — Helper `_bloquear_escrita(dest) -> liberar()`

```python
def _bloquear_escrita(dest_path):
    d = Path(dest_path)
    if os.name == "nt":
        subprocess.run(["icacls", str(d), "/deny", "*S-1-1-0:(WD)"], check=True, capture_output=True)
        def _liberar_windows():
            subprocess.run(["icacls", str(d), "/remove:d", "*S-1-1-0"], check=False, capture_output=True)
        return _liberar_windows
    os.chmod(d, stat.S_IRUSR | stat.S_IXUSR)
    def _liberar_posix():
        os.chmod(d, 0o755)
    return _liberar_posix
```

- `*S-1-1-0` = SID bem-conhecido **Everyone** → imune ao idioma do Windows (`icacls` aceita SID; nomes de grupo variam por locale).
- `(WD)` = WRITE_DAC/`write data`+`append data` → exatamente o que a criação de arquivo precisa; leitura continua permitida (cenário F exige o diretório acessível).
- `check=True` no deny (falha de simulação = teste falha com causa visível); `check=False` na liberação (cleanup tolerante).
- POSIX: ramos originais preservados byte-a-byte dentro do helper.

### D2 — Pontos de uso (2)

1. `test_destino_sem_permissao` (F): `try/finally` com `chmod` → `_bloquear_escrita`/`_liberar()`.
2. `test_zero_segredos_em_logs` (bloco F embutido): idem (dest2).

Nenhuma assertion alterada; `import os/stat/subprocess/Path` adicionados ao topo.

### D3 — Por que não outras opções

| Alternativa | Rejeição |
|---|---|
| Corrigir o service (probe pré-cópia de escrita) | Útil em produção (candidato futuro), mas desnecessário para os testes: a `PermissionError` já é mapeada; mudança de produção sem exigência funcional viola o mínimo-surpresa |
| Monkeypatch do `open`/`os.replace` no teste | Mascararia o caminho real de I/O que o cenário existe para exercitar |
| `skipif` no Windows | Esconderia o cenário F no SO onde o sistema roda hoje — pior opção |

## Riscos e mitigações

| Risco | Mitigação |
|---|---|
| `icacls` negar também o cleanup do `tmp_path` | Liberação em `finally` antes do `rmtree`; `/remove:d` tolerante |
| Locale/versão do Windows | SID bem-conhecido em vez de nome de grupo |
| POSIX quebrar | Ramos POSIX idênticos aos originais |

## Complexity Tracking

Nenhuma violação.
