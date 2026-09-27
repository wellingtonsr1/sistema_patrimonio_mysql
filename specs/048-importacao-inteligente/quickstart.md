# Quickstart: 048 — Importação Inteligente

**Validação ponta a ponta da feature.** Comandos usam `.venv/bin/python` (não `python` crua). Suíte baseline: **775 passed** (pós-047).

## Pré-requisitos

- Venv do projeto; banco de teste via `tests/conftest.py` (SQLite em memória, `client` autenticado como admin).
- Permissões vigentes de cada importador (`patrimonio.criar`, `colaboradores.criar`, `locais.criar`) — sem permissão nova.

## Como testar (manual)

1. Login como administrador → **Importar** → selecionar tipo (Equipamentos/Colaboradores/Locais) → enviar um CSV.
2. Passo **mapear colunas**: conferir sugestões (auto/ambígua/desconhecida), alterar e ignorar colunas, avançar.
3. **Pré-visualizar**: conferir resumo por classificação, filtros, avisos e resoluções por linha (NÃO ENCONTRADO).
4. **Confirmar**: conferir resumo final e `skip_duplicates`; gravar e conferir o relatório por linha.
5. Cancelar em qualquer fase → banco inalterado.

## Cenários do pedido → testes

| Teste | Cenário do pedido (§37–40) | Onde |
|---|---|---|
| A | CSV totalmente válido | `test_csv_totalmente_valido_importa_todos` |
| B | Registros parcialmente preenchidos (sem resp./sem local) | `test_registros_parciais_aceitos_sem_fabricar_valores` |
| C | CSV misto (válidos + inválidos) | `test_csv_misto_classifica_por_linha` |
| D | Tombamento duplicado no banco | `test_tombamento_duplicado_classificado_antes_gravacao` |
| E | Duplicidade dentro do próprio CSV | `test_duplicidade_interna_do_arquivo` |
| F | Colaborador inexistente | `test_responsavel_inexistente_resolucao_interativa` |
| G | Local inexistente | `test_local_inexistente_avisos_e_regras_atuais` |
| H | Colunas desconhecidas | `test_colunas_desconhecidas_marcadas_nao_utilizadas` |
| I | Mapeamento manual | `test_mapeamento_manual_alterado_e_aplicado` |
| J | Arquivo vazio | `test_arquivo_vazio_erro_compreensivel` |
| K | CSV inválido/corrompido | `test_csv_corrompido_erro_controlado` |
| L | Encoding/acentuação/BOM | `test_encoding_utf8_sig_e_acentos_preservados` |
| M | Cancelar antes da gravação | `test_cancelar_antes_gravacao_nao_altera_banco` |
| N | Erro durante gravação | `test_erro_gravacao_rollback_linha` |
| O | Auditoria | `test_confirmacao_registra_auditoria_com_quantidades` |
| P | Permissões | `test_importacao_bloqueada_sem_permissao` |
| Q | Regressão (suíte completa) | `.venv/bin/python -m pytest tests/ -q` → 775+ passed |

## Comprovações especiais

- **Análise não grava** (SC-001): nas fases de mapeamento e preview, contar registros antes/depois (`db_session.query(Asset).count()` etc.) → iguais; auditoria sem eventos novos.
- **Classificação correta** (SC-002): CSV misto semeado → resumo bate com as contagens esperadas por classe.
- **Compatibilidade (R9)**: todos os testes existentes dos 3 importadores passam **sem alteração** — com mapeamento aceito como sugerido o resultado é idêntico ao fluxo atual.
- **Responsável ausente**: nenhuma linha ganha custódia fabricada (sem "Sem responsável", sem colaborador parecido atribuído — FR-007/FR-008).
