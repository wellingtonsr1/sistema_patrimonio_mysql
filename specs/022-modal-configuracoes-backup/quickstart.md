# Quickstart — Configurações de Backup em Modal (feature 022)

> Validação end-to-end da feature. Seções: suíte automatizada, Testes A–H do briefing §28 (automatizável + manual) e validação visual em navegadores.

## 1. Pré-requisitos

```bash
# ambiente do projeto (venv existente)
python3 -m pytest -q            # suíte completa deve estar verde ANTES de começar (522 testes)
```

Aplicação rodando com usuário com perfil **Administrador** (permissão `backup.gerenciar`).

## 2. Suíte automatizada

```bash
# área de backup (config 021/022 + monitoramento + manual + automático + retenção + restore)
python3 -m pytest tests/test_backup_config.py tests/test_backup_monitoramento.py \
  tests/test_backup_manual.py tests/test_backup_automatico.py tests/test_backup_retencao.py \
  tests/test_backup_records.py tests/test_backup_restore.py -q

# suíte completa
python3 -m pytest -q
```

**Esperado**: 522 + testes novos da 022, **0 falhas**. Nenhum teste 020/021 removido ou enfraquecido (adaptações: `location` dos redirects e referências ao botão "Configurar").

## 3. Testes funcionais (briefing §28)

| # | Passo | Resultado esperado | Como validar |
|---|---|---|---|
| A — abrir | Na página Administração → Backups, clicar no ⚙ (topo direito) | Modal "⚙ Configurações de Backup" abre com os valores atuais | Manual (navegador) + automatizado (estrutura HTML do botão/modal) |
| B — fechar | Clicar no ✕ do cabeçalho do modal | Modal fecha; página permanece | Manual + automatizado (`btn-close` presente) |
| C — cancelar | Alterar um campo (ex.: retenção 30→60) e clicar **Cancelar** | Modal fecha; **nada é persistido** | Manual + automatizado (Cancelar é `type="button"` + `data-bs-dismiss`) |
| D — salvar | Alterar um campo válido (ex.: horário 02:00→23:00) e clicar **Salvar configuração** | Redirect para `/admin/backups?success=…`; alerta verde no topo; configuração persistida | Automatizado (fluxo 021 adaptado ao novo redirect) + manual |
| E — valores existentes | Com configuração já salva (23:00), reabrir o modal | Campos mostram 23:00 (não o default 02:00) | Automatizado (`value="23:00"` no HTML da página) + manual |
| F — backup automático | Após a mudança, ciclo automático/execução de testes 020 | Agendamento intacto | Automatizado (suíte) |
| G — retenção | Executar retenção / testes 020 | Política GFS intacta | Automatizado (suíte) |
| H — auditoria | Salvar uma alteração e consultar Auditoria | Evento `BACKUP_CONFIGURACAO_ALTERADA` com antes/depois | Automatizado (testes M 021) + manual na tela de auditoria |

## 4. Validação visual (manual — briefing §29/§14/§15)

### Larguras: 320 / 375 / 480 / 600 / 768 / 900 / 1024 / 1280 / 1366 / 1440 / 1920 px (DevTools)

Em cada largura, verificar:

- [ ] ⚙ à direita, alinhado ao título "Backups", sem sobreposição (em < ~480 px pode quebrar para a linha de baixo — `flex-wrap`);
- [ ] Modal sem **scroll horizontal**; campos reorganizados em 1 coluna nas larguras pequenas; botões Cancelar/Salvar acessíveis; ✕ visível;
- [ ] Página: card "Backup Automático" e "Gerar backup agora" normais; seção de configuração **não** aparece na página.

### Navegadores e temas

- [ ] Chrome — tema claro
- [ ] Chrome — tema escuro
- [ ] Firefox — tema claro
- [ ] Firefox — tema escuro

Verificar no modal: fundo, texto, bordas, campos, placeholder, selects, botões, foco, overlay e ✕ herdam o tema como nos demais modais (ex.: conferência de inventário).

### Fluxo completo de sensação de uso (smoke)

1. Login admin → Administração → Backups → página limpa (sem seção de config);
2. ⚙ → modal abre com valores atuais → Cancelar → nada mudou;
3. ⚙ → alterar horário → Salvar → alerta de sucesso no topo;
4. ⚙ → reabrir → valor novo presente;
5. Gerar backup → fluxo manual normal (fora do modal);
6. Indicadores do card "Backup Automático" presentes e inalterados.

## 5. Regressão (briefing §30)

- [ ] Página Backups carrega (200) com e sem backups;
- [ ] Backup manual (gerar/baixar) funciona;
- [ ] Backup automático: card com indicadores; (opcional, ambiente real) ciclo dispara;
- [ ] Retenção: indicadores "Última retenção"/"Removidos" presentes;
- [ ] Restauração: página de confirmação e fluxo 017/019 intactos;
- [ ] Auditoria: evento de configuração aparece;
- [ ] Permissões: usuário **Consulta** → página Backups negada (guard existente); POST direto sem permissão → 403;
- [ ] Navegação, tema claro/escuro normais.

## 6. Critérios de aceite (briefing §31) — checklist final

- [ ] Seção "Configurações de Backup" não ocupa espaço na página (só no modal)
- [ ] Conteúdo disponível via modal; todos os campos atuais presentes (mesmos `name=`)
- [ ] Botão somente-ícone ⚙, à direita do título, alinhado, com tooltip/aria-label "Configurações de Backup"
- [ ] Modal no padrão visual dos modais existentes (sem CSS/JS novo)
- [ ] Valores atuais carregados; Cancelar não salva; Salvar usa o mecanismo existente
- [ ] Backup automático, retenção, auditoria, RBAC, claro/escuro, responsividade — íntegros
- [ ] Zero alteração de banco; zero novo mecanismo de configuração; zero funcionalidade não relacionada alterada
