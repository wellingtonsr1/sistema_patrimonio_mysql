# Research — Configurações de Backup em Modal (feature 022)

*Decisões de design baseadas na análise do código real. Nenhum NEEDS CLARIFICATION restante.*

## R1 — Como a página principal obtém `config_form` sem efeito colateral de escrita

**Problema**: a 021 deliberadamente NÃO passava `config_form` para `GET /admin/backups`, porque `get_backup_config(db)` cria a linha singleton `id=1` e **commita** quando ausente. Um GET que grava no banco quebrou testes da suíte (transação do fixture morta por commit de outro caminho) e viola a semântica de leitura da página.

**Decisão**: parâmetro aditivo `create: bool = True` em `get_backup_config(db, create=True)` e `get_effective_config(db, create=True)`:
- `create=True` (default): comportamento **idêntico ao atual em todos os chamadores existentes** (rota da config, scheduler via service, POST) — nada muda;
- `create=False`: leitura pura — se a linha não existe, retorna um objeto **não persistido** (ou efetiva resolvida a partir dele) sem `add`/`commit`; a resolução da efetiva funciona igual (campos None → env → default).

**Justificativa**: menor alteração possível que elimina o efeito colateral (vs. alternativas: duplicar lógica de leitura no template — viola camadas; pré-criar a linha no startup — mudança de comportamento além do escopo). Compatível 100%: nenhum chamador precisa mudar.

## R2 — Estrutura do modal (referência: Modal de Conferência do Bem)

**Verificado** em `inventarios/detail.html` (`modalConferir`):
```html
<div class="modal fade" id="..." tabindex="-1" aria-hidden="true">
  <div class="modal-dialog">            <!-- (variante confirmar-encerrar) -->
    <div class="modal-content">
      <form method="post" action="...">
        <div class="modal-header">
          <h5 class="modal-title">...</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fechar"></button>
        </div>
        <div class="modal-body"> ... campos ... </div>
        <!-- footer: d-flex justify-content-end gap-2 com btn-outline-secondary + btn de ação -->
      </form>
    </div>
  </div>
</div>
```

**Decisão**: replicar exatamente essa estrutura em `backups.html` com id `#modalBackupConfig`:
- `modal-header`: `<h5 class="modal-title"><i class="bi bi-gear me-1"></i>Configurações de Backup</h5>` + `btn-close` (`data-bs-dismiss`, `aria-label="Fechar"`);
- `modal-body`: o formulário atual **inteiro** (mesmos `name=`, `value=`, labels, `form-text` da descrição de pré-restauração; grade `row g-3` com colunas `col-sm-6`/`col-12` — reorganiza em telas pequenas);
- Footer: **Cancelar** (`btn-outline-secondary`, `type="button"`, `data-bs-dismiss="modal"` — fora do fluxo de submit, nada persiste) + **Salvar configuração** (`btn-primary`, `type="submit"`).

Alternativas descartadas: modal "estático" custom com JS próprio (cria biblioteca nova — proibido §34); `modal-lg` vs. default — usar `modal-dialog modal-lg` **apenas se** a grade de 8 campos apertar; decisão final: `modal-dialog modal-dialog-centered modal-lg` (melhor uso do espaço para 2 colunas, ainda Bootstrap puro).

## R3 — Botão ⚙ e alinhamento ao título

**Verificado**: `page-header` atual de `backups.html` é `<div class="page-header"><div><h3>…</h3><p>…</p></div></div>` (sem flex). O sistema usa `d-flex justify-content-between align-items-center` em vários lugares (card "Gerar backup", cards de perfil).

**Decisão**: transformar o bloco do header em flex —
```html
<div class="page-header d-flex justify-content-between align-items-start flex-wrap gap-2">
    <div>
        <h3 class="page-header-title">Backups</h3>
        <p class="page-header-subtitle">…</p>
    </div>
    <button type="button" class="btn btn-sm btn-outline-primary" data-bs-toggle="modal"
            data-bs-target="#modalBackupConfig"
            aria-label="Configurações de Backup" title="Configurações de Backup">
        <i class="bi bi-gear"></i>
    </button>
</div>
```
- `align-items-start` + botão no topo: engrenagem alinhada **verticalmente ao título** (não ao bloco inteiro) em qualquer largura;
- `flex-wrap`: em telas estreitas o botão quebra para baixo do título sem sobreposição (§14);
- Somente ícone (§2/§7): sem texto; tooltip nativo via `title`; `aria-label` para leitores de tela;
- `btn-outline-primary btn-sm`: padrão de botão de ícone/ação secundária já usado (o antigo botão "Configurar" era `btn-sm btn-outline-primary` — mesmo vocabulário visual).

## R4 — Redirect do POST: de volta para a página principal

**Hoje**: `POST /admin/backups/configuracoes` → 303 `/admin/backups/configuracoes?success=…|error=…` (a página do formulário dedicado).

**Com o modal na página principal**: o redirect passa a ser **`/admin/backups?success=…|error=…`** — o usuário vê a mensagem no alerta do topo da página de Backups (padrão server-rendered; o modal nasce fechado após o reload). A rota da página dedicada **permanece** (compatibilidade: bookmarks, testes existentes, acesso direto) e continua funcional: seu formulário vira o mesmo modal reutilizado no template (o template é único — `backups.html` serve as duas rotas).

**Impacto em testes 021**: `test_k`/`test_f`/etc. assertam `location` com `/admin/backups/configuracoes?success=` → adaptação legítima (assert passa a ser `/admin/backups?success=`; mesmas garantias, mesmo fluxo). **Zero** enfraquecimento.

## R5 — RBAC do botão ⚙ e do modal

**Verificado**: `GET /admin/backups` já exige `require_permission("backup.gerenciar")` — todo HTML da página (incluindo ⚙ e modal) só é renderizado para autorizados. O POST continua com o guard próprio (403 direto).

**Decisão**: nenhuma permissão nova, nenhum guard novo (§22/§34). O `config_form` passado à página herda a mesma proteção do guard existente. Observação: a spec exige "⚙ não aparece sem permissão" — já garantido pelo guard da página (usuário sem permissão nem chega a renderizar).

## R6 — Testes automatizados cobríveis (o que é automatizável)

Testes A (abrir) e B (fechar/X/Cancelar) são **comportamento do Bootstrap** (`data-bs-*`) — não executam JS em TestClient. Cobertura automatizada honesta:
- **Estrutura**: na página `/admin/backups` existe o botão com `aria-label="Configurações de Backup"`, `data-bs-target="#modalBackupConfig"`, ícone `bi bi-gear` **sem texto**; existe `div` com `id="modalBackupConfig"` + classes `modal`/`modal-header`/`btn-close`/`modal-footer`; os 8 campos (`name=`) aparecem **exatamente 1 vez** no HTML da página (dentro do modal; seção antiga fora do modal não existe mais);
- **Valores atuais** (Teste E): após salvar 23:00 via POST, `GET /admin/backups` contém `value="23:00"` no campo time dentro do modal;
- **Cancelar** (Teste C): é estático (`type="button"` + `data-bs-dismiss` — não submete form) → validado por **estrutura** (`type="button"`, `data-bs-dismiss="modal"`, fora de `type="submit"`);
- **Salvar** (Teste D) + **auditoria** (H) + **403**: já automatizados e permanecem (fluxo inalterado);
- **Backup/retenção intactos** (F/G): suíte 020/021 verde;
- **Visual real** (A/B/temas/responsividade): validação **manual** por quickstart (navegadores, larguras, claro/escuro) — padrão das features anteriores.
