# Service Contract — Configurações de Backup em Modal (feature 022)

> Padrão das specs 015–021: nomes finais podem variar minimamente na implementação, semântica não. Escopo: template + leitura aditiva no service + redirect da rota. Nada mais.

---

## §1. `app/services/backup_config_service.py` (única mudança de código Python)

### Assinaturas

```python
def get_backup_config(db: Session, create: bool = True) -> BackupConfig
def get_effective_config(db: Session, create: bool = True) -> EffectiveBackupConfig
```

### Comportamento

| Caso | `create=True` (default) | `create=False` |
|---|---|---|
| Linha `id=1` existe | retorna a linha | retorna a linha |
| Linha `id=1` **não** existe | cria (`add`+`commit`+`refresh`) e retorna — **comportamento atual** | retorna objeto **não persistido** `BackupConfig(id=1, auto_enabled=False)` sem add/commit/flush |
| `get_effective_config` | resolve igual hoje | resolve igual hoje (campos `None` → env → default) |

### Garantias

- Nenhum chamador existente precisa mudar (default preserva o comportamento);
- `create=False` nunca grava (invariante de GET somente-leitura);
- `save_backup_config` **não muda** (valida-tudo-antes → commit único);

### Matriz de erros

| Cenário | Resultado |
|---|---|
| Banco indisponível na leitura (`create=False`) | Exceção propaga (mesmo tratamento de hoje nas rotas) — sem estado parcial |
| Objeto não persistido renderizado | Atributos simples (`str/int/bool/None`) — nenhum lazy-load; render seguro |

---

## §2. Rotas (`app/web/admin_routes.py`)

### `GET /admin/backups` (listagem — página principal)

- Guard existente: `require_permission("backup.gerenciar")` — **inalterado**;
- Contexto **ganha**: `config_form = get_effective_config(db, create=False)` — pré-preenche o modal;
- **Não** chama `get_backup_config` (nem com `create=False`): a listagem não precisa da linha;
- Demais variáveis de contexto (`backups`, `auto_status`, `retention_summary`, `types_by_filename`, `success`, `error`, `info`, `restore_status`, `active_tab`) inalteradas.

### `GET /admin/backups/configuracoes` (rota dedicada — MANTIDA por compatibilidade)

- Comportamento atual preservado (contexto com criação — `create=True`);
- Renderiza o **mesmo template** → exibe a página com o modal (aberto ou fechado: fechado; o acesso direto mostra a página normal com o ⚙).

### `POST /admin/backups/configuracoes`

- Guard, validação, persistência, auditoria: **inalterados**;
- **Única mudança**: redirect 303 de volta para a **página principal**:
  - sucesso → `/admin/backups?success=<msg>`
  - erro de validação → `/admin/backups?error=<msg>`
- Motivo: o formulário agora vive no modal na página principal; a mensagem aparece no alerta do topo (padrão existente) e o modal nasce fechado após o reload.

### Matriz de erros (rotas)

| Cenário | Resultado |
|---|---|
| POST sem permissão | 403 (inalterado) |
| POST com valor inválido | 303 `?error=<motivo>` — configuração vigente intacta (inalterado) |
| POST com sucesso | 303 `?success=<msg>` + evento `BACKUP_CONFIGURACAO_ALTERADA` (inalterado) |

---

## §3. Template `app/web/templates/admin/backups.html`

### Header da página (§6 do briefing)

```html
<div class="page-header d-flex justify-content-between align-items-start flex-wrap gap-2">
    <div>
        <h3 class="page-header-title">Backups</h3>
        <p class="page-header-subtitle">…(atual)…</p>
    </div>
    <button type="button" class="btn btn-sm btn-outline-primary"
            data-bs-toggle="modal" data-bs-target="#modalBackupConfig"
            aria-label="Configurações de Backup" title="Configurações de Backup">
        <i class="bi bi-gear"></i>
    </button>
</div>
```

- Somente ícone (sem texto); tooltip `title`; `aria-label`; alinhado ao título; sem posicionamento absoluto; `flex-wrap` evita sobreposição em telas estreitas.

### Remoções

- Card/seção "Configurações de Backup" deixa de existir **fora** do modal;
- Botão "Configurar" do card "Backup Automático" (navegação provisória da 021) é **removido** — substituído pelo ⚙.

### Modal (id `#modalBackupConfig` — estrutura do modalConferir)

```html
<div class="modal fade" id="modalBackupConfig" tabindex="-1" aria-hidden="true" aria-labelledby="modalBackupConfigLabel">
  <div class="modal-dialog modal-lg modal-dialog-centered">
    <div class="modal-content">
      <form method="post" action="/admin/backups/configuracoes">
        <div class="modal-header">
          <h5 class="modal-title" id="modalBackupConfigLabel"><i class="bi bi-gear me-1"></i>Configurações de Backup</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fechar"></button>
        </div>
        <div class="modal-body">
          <!-- EXATAMENTE os campos atuais: mesmos name=, value=, labels, form-text -->
          <!-- grade row g-3: auto_enabled (col-12 switch), schedule, time, weekday,
               keep_pre_restore (+ descrição), retention_daily_days, retention_weekly_weeks,
               retention_monthly_months -->
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancelar</button>
          <button type="submit" class="btn btn-primary"><i class="bi bi-save me-1"></i>Salvar configuração</button>
        </div>
      </form>
    </div>
  </div>
</div>
```

### Invariantes do template

1. Os 8 campos com os mesmos `name=` aparecem **1 única vez** no HTML (dentro do modal);
2. `config_form` pré-preenche `value=`/`selected`/`checked` (valores atuais — nunca defaults fixos);
3. **Zero** `<script>` novo; **zero** CSS novo; só classes Bootstrap/variáveis do tema já usadas;
4. `{% if config_form %}` guarda o modal (sem contexto → sem modal; mesma proteção da seção atual);
5. Cards "Backup Automático" (indicadores) e "Gerar backup agora" ficam **fora** do modal, intocados (exceto remoção do botão "Configurar").

---

## §4. Auditoria e RBAC

- **Auditoria**: nenhum evento novo/alterado — `BACKUP_CONFIGURACAO_ALTERADA` com before/after continua gravado pelo POST existente (Teste H);
- **RBAC**: nenhuma permissão nova/alterada — `backup.gerenciar` na página (guard existente) e no POST (403 direto, inalterado).

---

## §5. Contrato de testes (mapeamento briefing §28)

| Teste | Cobertura | Verificação |
|---|---|---|
| A — abrir | Comportamento Bootstrap (`data-bs-*`) | Automatizada: presença do botão ⚙ com `data-bs-target="#modalBackupConfig"` + modal no HTML; manual: clique real |
| B — fechar (X/Cancelar) | Estrutura estática | `btn-close`/Cancelar com `data-bs-dismiss="modal"` e `type="button"`; manual: interação |
| C — cancelar não salva | Estrutura | Cancelar fora do submit; + Teste E confirma valores vigentes ao reabrir |
| D — salvar | Fluxo existente | POST 303 `?success=` em `/admin/backups`; persistência (Teste K 021 adaptado) |
| E — valores existentes | Render | Após salvar 23:00, `GET /admin/backups` contém `value="23:00"` (no modal) |
| F — backup automático intacto | Regressão | Suíte 020 (agendamento) verde |
| G — retenção intacta | Regressão | Suíte 020 (retenção) verde |
| H — auditoria | Regressão | Testes M 021 verdes (evento com before/after) |

**Adaptações legítimas de testes 021** (sem enfraquecimento): `location` dos redirects (`?success=`/`?error=` agora em `/admin/backups`); verificações de HTML que citam o botão "Configurar" (passam a citar o ⚙). Zero teste removido; asserts equivalentes ou mais fortes.

---

## §6. Compatibilidade

- Rota dedicada mantida (bookmarks/links antigos seguem funcionando);
- Suíte em SQLite e produção MariaDB/Windows/Linux: mudança é template + leitura — sem dependência de plataforma;
- Temas claro/escuro e responsividade: herdados do Bootstrap/variáveis existentes (sem CSS novo).
