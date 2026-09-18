# Data Model: Backup Manual — Briefing Completo

**Feature**: 016-backup-manual-completo | **Data**: 2026-09-17

> **Zero DDL mantido** (§10/§31): nenhum metadado persistido em banco — checksum, tamanho e timestamp derivam do arquivo.

---

## 1. Artefato v2

| Atributo | Valor |
|---|---|
| Nome final | `backup_YYYYMMDD_HHMMSS_micros.sql.gz` (gzip streaming do dump SQL MariaDB — UTC com microssegundos) |
| Nome temporário | `<base>.part` (dump SQL) → `<base>.part.gz` (comprimido) — mesmo nome-base único; nenhum casa o regex final (**remediação I1**: esquema do contract padronizado) |
| Regex aceita (listagem/download) | `^backup_\d{8}_\d{6}_\d{6}\.sql(\.gz)?$` — **compatibilidade**: `.sql` da 015 e `.sql.gz` novos |
| SHA-256 | Derivado do arquivo final, em streaming; viaja no evento `BACKUP_CRIADO` (`new_data.sha256`) e na listagem (on-demand) |
| Unicidade | Microssegundos (BV-3 mantido) + `.part` herda o nome-base (sem colisão de temporários, §20) |

## 2. Estados da geração (v2 — atômica, §27)

```text
[Solicitado] ── permissão? ──n──> 403 (auditado — 015, preservado)
     │ sim
     ▼
[LOG info: início] ──> dump nativo → <base>.part
     │
     ▼
gzip streaming → <base>.part.gz (blocos 1 MB, memória constante)
     │
     ▼
validação: arquivo existe + tamanho > 0 + gzip legível
     ├── falha ──> remove .part* ──> BACKUP_FALHA (FALHA, desc. segura)
     │                                   + log error (sem segredos) + erro controlado ao usuário
     ▼
SHA-256 (streaming)
     ▼
RENOMEAR .part.gz → backup_....sql.gz   (atômico, mesmo filesystem)
     ▼
BACKUP_CRIADO (SUCCESS, new_data: arquivo, tamanho_bytes, sha256) + log info
     ▼
redirect com confirmação
```

**Invariantes novos** (v2):

- **BV-8** — Em nenhum instante existe arquivo que case o regex final e esteja incompleto: o nome final só surge pela renomeação pós-validação (§27).
- **BV-9** — Todo backup `.sql.gz` listado possui SHA-256 recomputável e gzip legível (Integridade OK); falha na leitura/trailer → status CORROMPIDO na listagem, nunca OK (§16/§18).
- **BV-10** — Backups `.sql` (015) mantêm listagem/download; Integridade = **—** (sem checksum retroativo).
- **BV-11** — Log técnico contém início/conclusão/falha da geração; jamais credenciais/comando/stderr bruto (§26).

## 3. Auditoria (trilha existente — sem mecanismo paralelo, §25)

| Evento | Quando | new_data |
|---|---|---|
| `BACKUP_CRIADO` / SUCCESS | renomeação concluída | `{"arquivo": filename, "tamanho_bytes": n, "sha256": hash}` (campo aditivo) |
| `BACKUP_FALHA` / FALHA (**novo**, I1) | qualquer falha do fluxo | sem new_data; `description` segura (§19) |
| `BACKUP_DOWNLOAD` / SUCCESS | download servido | `{"arquivo": filename}` (inalterado) |

Rótulos de exibição: "Backup Gerado" / **"Backup Falhou"** (novo) / "Download de Backup". Eventos históricos da 015 intocados (trilha imutável).

## 4. Compatibilidade de transição

| Formato | Gerado por | Listagem | Download | Integridade |
|---|---|---|---|---|
| `.sql` | 015 | sim | sim | **—** |
| `.sql.gz` | 016+ | sim | sim | OK / CORROMPIDO |
| `<base>.part` | 016 (em voo) | **não** (regex) | não | n/a |

## 5. Interface (coluna nova, §18)

Listagem: Arquivo · Data/Hora (UTC) · Tamanho · **Integridade** (OK / — / CORROMPIDO) · **SHA-256** (truncado, `title` com hash completo) · Ações (Baixar). Componentes/tema/responsividade existentes preservados.
