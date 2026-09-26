# Validação: Ajuste Responsivo da Tabela "Usuários do Sistema" (043)

**Data**: 2026-09-25 · **Branch**: `043-usuarios-larguras-colunas` · **Formato**: 036–042

## 1. Suíte de testes (SC-006)

| Momento | Comando | Resultado |
|---|---|---|
| Baseline (T002) | `python -m pytest tests/ -q` | 1ª execução com 1 falha transitória do ambiente; **confirmação: 728 passed** |
| Focado pós-alteração (T006) | `pytest tests/test_help.py tests/test_rbac.py tests/test_auth.py -q` | **56 passed** |
| Completo pós-alteração | `python -m pytest tests/ -q` | **728 passed** |

- Não existe arquivo de testes dedicado a admin/users (T002/T005 do plan previam essa verificação) — o run focado usa `test_help.py` + `test_rbac.py` (que valida strings desta página, L213/221) + `test_auth.py` (domínio de usuários).

## 2. Baseline "antes" (V0 — seção 29 do pedido)

Distribuição do layout automático (sem colgroup/`:style`): as 7 colunas competiam por espaço sem priorização — e-mails e nomes completos quebravam; "Active Directory" e Perfis podiam transbordar (nowrap embutido do `.badge`); Último Acesso/Ações já tinham `text-nowrap` próprios. Screenshot/contagem de quebras registrados na execução local (saída integral em `validacao_local.out.md`).

## 3. Comparação antes/depois (V1 — SC-001/SC-002)

Conjunto final (medições `validar_local.py`):

| Viewport | Usuário | E-mail | Origem | Perfis | Status | Último Acesso | Ações |
|---|---|---|---|---|---|---|---|
| 1440px | 222,6px (15,5%) | **272,6px (19,0%)** | 192,6px (13,4%) | 222,6px (15,5%) | 162,6px (11,3%) | 222,6px (15,5%) | 142,6px (9,9%) |
| 1024px | 163,1 | **213,1 (20,9%)** | 133,1 | 163,1 | 103,1 | 163,1 | 83,1 |
| 375px (piso) | 150 | **200** | 120 | 150 | 90 | 150 | 70 |

- **Nota de medição**: o WeasyPrint distribui o excedente do container entre as colunas; os valores de 1440/1024px refletem a tabela expandida (~1438px). O piso por coluna é o que a tabela mantém em janelas menores (375px): Usuário 150 · E-mail 200 · Origem 120 · Perfis 150 · Status 90 · Último Acesso 150 · Ações 70 = **1330px = min-width** — em navegadores reais, rolagem confinada abaixo de ~1470px de janela.
- Textuais (Usuário+E-mail+Perfis) dominam: **50%** da tabela (SC-002 ✓); tabela em 100% da largura útil (SC-001 ✓).
- **Linha garantida**: username e full_name com `.usr-ellip` (nowrap + ellipsis + tooltip) — ícone e badge ADMIN fora dos spans cortáveis; e-mail idem; badges íntegros; data/hora sem quebra (`text-nowrap` original).

## 4. Larguras finais adotadas (T003/T005 — C-1)

Conjunto **único** em px (soma 1330px → `min-width: 1330px`), sem media query de colunas (lição da 041):

| Col | Coluna | Final | Piso verificado (×1,25–1,30 da fonte real) |
|---|---|---|---|
| c1 | Usuário | 150px | username + ícone (~90px); full_name corta com tooltip |
| c2 | E-mail | 200px | maior coluna; e-mails reais longos cortam com tooltip |
| c3 | Origem | 120px | "Active Directory" com ícone (~110px) — ou quebra entre palavras (badge `white-space: normal`) |
| c4 | Perfis | 150px | badges sem ellipsis (C-6); flex-wrap organiza entre badges |
| c5 | Status | 90px | "Bloqueado" ~78px + padding |
| c6 | Último Acesso | 150px | "25/09/2026 18:30" ≈ 127px + padding (nowrap) |
| c7 | Ações | 70px | 1 botão-icon 32px + padding (condição `usuarios.editar` preservada) |

## 5. Resultado por cenário

- **V1 (desktop)**: ✓ §3. Sem grandes vazios; sem colunas excessivamente estreitas; linha garantida.
- **V2 (conteúdos + tooltips)**: ✓ tooltip Bootstrap em username, full_name e e-mail (marcação server-rendered, inicialização existente — base.html/main.js); badge "ADMIN" íntegro ao lado do username; "Active Directory" com ícone (quebra só entre palavras se a coluna for estreita); Perfis com badges íntegros sem ellipsis, flex-wrap preservado, "Sem perfil" intacto; Status Ativo/Bloqueado; "Nunca" sem quebra; Editar condicional a `usuarios.editar`. *(Confirmação de hover no navegador no aceite final.)*
- **V3 (alinhamento/estabilidade)**: ✓ 7/7 sob os cabeçalhos; distribuição idêntica nas 4 linhas do seed (admin/AD/sem perfil/bloqueado) e entre temas; alturas uniformes.
- **V4 (responsividade)**: ✓ 1440/1024: tabela expande com o container (soma = container); 375px: piso mantido (930px) com rolagem confinada ao `table-responsive` (comportamento esperado — em navegadores reais o min-width 1330px impõe rolagem antes); zoom 80–200% coberto pela estabilidade px; temas idênticos.
- **V5 (não-vazamento)**: ✓ `git diff` = apenas `admin/users/list.html`; `style.css`/`sw.js` intocados; **nenhuma mudança de impressão** (tela não-relatório — R10); telas 036–042 inalteradas.

## 6. Zoom 80%–200%

Colunas px mantêm a distribuição em toda a faixa por construção; em janelas < ~1470px a rolagem confinada aparece (min-width 1330px); nenhuma fonte reduzida.

## 7. Observações

1. **Falha transitória no baseline**: 1ª execução da suíte completa acusou 1 falha sem FAILED identificável na re-execução — padrão de contenção do ambiente já observado na 042; confirmação limpa: **728 passed**.
2. **Sem testes dedicados a admin/users**: o plan previa identificá-los no T002; constatada a inexistência, o focado ficou em help+rbac+auth (56 passed).
3. **Sem bloco de impressão** (R10): tela não-relatório — nenhum `@media print` criado; a impressão segue o comportamento global (fora do escopo).
4. **Tooltip sempre presente no markup** (F3 do analyze): decisão simples — tooltips redundantes em valores não truncados são inofensivos e não exigem JS novo.
5. **WeasyPrint não impõe `min-width`**: estabilidade verificada por coluna (pisos em 375px = larguras do colgroup); em navegadores reais a rolagem confinada ocorre abaixo de ~1470px de janela.
6. Nenhuma interação com `tag-badge` ≤479px (este template não usa `tag-badge`).

## 8. Decisões finas

- `.usr-ellip` como span interno: separa a área cortável do ícone e do badge ADMIN (o badge nunca é truncado — elemento funcional).
- Tooltips nas **duas linhas** do Usuário (username e full_name), cada uma com seu valor completo (clarificação).
- `white-space: normal` escopado em `.usr-lista-table .badge`: protege "Active Directory"/labels de Perfis do transbordo (lição 042), quebrando apenas entre palavras.
- Perfis sem ellipsis: dado funcional (papéis do usuário) — organização via flex-wrap é o fallback da spec (C-6).
- Seed do medidor cobre os edge cases do quickstart (admin/ADMIN, AD/Local, com/sem full_name, com/sem perfis, bloqueado, "Nunca").
