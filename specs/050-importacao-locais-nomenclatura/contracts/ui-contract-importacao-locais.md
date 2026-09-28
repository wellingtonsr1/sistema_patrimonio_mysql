# UI Contract — Importação/Exportação de Localizações (Feature 050)

**Escopo**: superfícies do domínio de locais tocadas pela 050. Padrão dos contratos das features 036–048.

## §1 DOM/funcionalidade protegida (não pode quebrar)

| Elemento | Localização | Proteção |
|---|---|---|
| Formulário de importação (upload + skip_duplicates) | `locations/import.html` | campos/ids/ação inalterados |
| Passo de mapeamento (`include imports/_mapping_step.html`) | parcial compartilhado | selects por coluna, opções `field_labels`, confirmação — lógica intocada (só os rótulos de locations mudam via service) |
| Prévia inteligente (`imports/_smart_preview.html`) | parcial compartilhado | colunas Linha/Identificador/Situação/Problema + filtros + resolução interativa — intocados |
| Prévia tradicional (tabela com `<th>`) | `locations/import.html` L178+ | estrutura da tabela, badges "Novo"/"Duplicata", colunas de dados inalterados (só o texto de 2 `<th>`) |
| Botões Confirmar/Cancelar | fluxo de confirmação | posições/estilos inalterados (padrão da 7a4c3f6) |
| Listagem de locais | `locations/list.html` | já oficial — nenhuma edição prevista |
| Formulário de localização | `locations/form.html` | já oficial — nenhuma edição prevista |

## §2 Conteúdo que não pode sumir

- Prévia tradicional: nome, unidade administrativa, departamento, prédio, andar, sala, gestor, status (Novo/Duplicata) por linha.
- Ajuda da tela de importação (L286–357): tabela de colunas + exemplo `Localização;Unidade Administrativa;Departamento;...` — já oficial, preservar.
- Mensagens de erro por linha na prévia inteligente (`problems`) — continuam exibidas, agora com texto oficial.
- Selects do mapeamento: todas as opções de campo permanecem (nenhum campo removido de `FIELD_LABELS`).

## §3 Comportamento por superfície (estado alvo)

| Superfície | Antes | Depois |
|---|---|---|
| Upload CSV oficial novo | Erro: "filial é obrigatória" (não importa) | Mapeamento sugerido correto (Localização/Unidade Administrativa/Departamento) → classificação → importação OK |
| Upload CSV legado (`Nome;Filial;Departamento`) | Funciona | Continua funcionando (compatibilidade FR-006) |
| Mensagem de linha inválida | "nome/filial é obrigatório(a)" | "Localização é obrigatória" / "Unidade Administrativa é obrigatória" |
| Export `locais.csv` | header legado | header oficial; arquivo reimportável direto (round-trip) |

## §4 Não-vazamento (V5)

- `diff` confinado a: `location_import_service.py`, `import_intelligence.py` (só `FIELD_LABELS["locations"]`), `report_service.py` (só `generate_locations_csv`), `templates/locations/import.html`, testes do domínio, docs de locais.
- `imports/_mapping_step.html` e `imports/_smart_preview.html` (parciais compartilhados com equipamentos/colaboradores): **nenhuma edição** — rótulos mudam só para locations via service.
- Outras telas/entidades: nenhum seletor, texto ou lógica alterados.

## §5 Critérios de violação

1. Qualquer edição nos parciais `imports/_*.html` → violação (código morto ou risco às outras entidades).
2. Qualquer mudança em `execute_locations_import` / rotas / permissões → violação.
3. Novo CSS global ou alteração visual além dos textos → violação.
4. Alias novo fora da lista oficial+legada (§2.2 do data-model) → violação (FR-008).
