# Data Model: Correção da Documentação da Configuração de Backup

**Feature**: 025 | **Data**: 2026-09-19
**Natureza**: a feature não cria nem altera entidades de produção. O "modelo de dados" aqui é o **modelo de conteúdo** das edições documentais e os fatos de código que as sustentam.

---

## 1. Entidade de entrega: `DocEdit` (contrato `doc-edit-contract.md` §1)

| ID | Arquivo | Localização | Correção | Achado |
|---|---|---|---|---|
| E1 | `docs/GUIA_DE_MANUTENCAO.md` | ~L113 (fim do parágrafo "Onde ficam as configurações?") | fallback "primeira inicialização" → fallback por campo + bootstrap + AT-3 | AT-1 + AT-3 |
| E2 | `README.md` | ~L972–973 (parágrafo da precedência) | "fallback na primeira inicialização" → fallback por campo; precedência atribuída a `get_effective_config()`; + parágrafo do fallback de boot (exceção) | AT-1 + AT-2 |
| E3 | `README.md` | após ~L994 ("Valores inválidos…") | inserir nota da particularidade de `BACKUP_AUTO_ENABLED` (não-nullable) | AT-3 |
| E4 | `docs/ARQUITETURA_E_MANUTENCAO.md` | ~L1215 (registro do fluxo de config) | cláusula do fallback de boot (snapshot anterior → env/default) | AT-2 |

**Regras**: E1–E4 são as ÚNICAS edições permitidas; cada uma tem localização, texto-alvo (research R1–R4) e invariante de preservação.

## 2. Fatos de código que sustentam as edições (verificados — nunca alterados)

| Fato | Evidência | Usado em |
|---|---|---|
| Precedência por campo: persistido → env → default | `backup_config_service.py:122–185` (`_first_defined`/`_effective_int`) | E1, E2 |
| `get_effective_config()` centraliza a resolução | `backup_config_service.py:106` (5 chamadores — 024 §3.2) | E1, E2 |
| Fallback de boot: falha → snapshot anterior → sem snapshot → env/default | `backup_scheduler.py:107–124` (log "mantendo snapshot anterior" `:110`) | E1, E2, E4 |
| `auto_enabled` não-nullable; env não reconsultada dinamicamente | `models/backup_config.py:23` + `backup_config_service.py:155` | E1, E3 |
| Tick de 30 s; aplicação sem reinício | `backup_scheduler.py:64,790,799` | contexto E2/E4 |
| Defaults 020: `false/daily/02:00/0/30/12/12/0` | `config.py:67–87` = `_DEFAULT_*` (`backup_config_service.py:25–32`) | contexto E2/E3 |
| Instalação nova nasce desativada | `config.py:67` + criação lazy `backup_config_service.py:72–76` | contexto E1/E3 |
| Retenção consome a efetiva | `backup_scheduler.py:625–628` | contexto E4 |

## 3. Entidade de entrega: `FinalReport` (relatório — briefing §39)

**Arquivo**: `specs/025-documentacao-config-backup/relatorio.md`. Conteúdo obrigatório (13 itens): arquivos alterados; correção por arquivo; tratamento de AT-1/AT-2/AT-3; confirmações de preservação (config.py funcionalmente intacto, 8 constantes, scheduler, service, banco, testes); verificações realizadas; divergências para feature futura.

## 4. Estados e transições (conteúdo documental)

```text
Documento com afirmação incorreta/incompleta (AT-x identificado pela 024)
  ↓ E1–E4 (única transição permitida)
Documento fiel ao código atual
  ✗ nunca: alterar código para "casar" com a doc; criar 2ª fonte; reescrever além do necessário
```

## 5. Relacionamentos com entidades de produção (somente referência documental)

- `backup_config` (singleton id=1) — citada como local de persistência (E1).
- `get_effective_config()` — citada como resolvedor da precedência (E1, E2).
- `EffectiveBackupConfig`/snapshot — citados no mecanismo de atualização sem reinício e no fallback de boot (E2, E4).
- Nenhuma entidade de produção é criada, alterada ou removida.
