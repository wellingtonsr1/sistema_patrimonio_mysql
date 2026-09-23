# Ofício — Solicitação de Acesso à API 1Doc (Feature 031)

**Data**: 2026-09-23
**Origem**: Feature 031 (Integração 1Doc) — pendência externa Fase 1 (itens C-1..C-8 da spec)
**Status**: Modelo para adaptação — preencher os campos entre colchetes
**Arquivo complementar**: `docs/SOLICITACAO_API_1DOC.md` (versão e-mail + notas internas)

---

<!-- Preencher: número sequencial do ofício do setor no ano corrente -->
**Ofício nº [XXX]/2026 — [Setor de Patrimônio/IPMJP]**

**Ao**  
[Fornecedor 1Doc — Razão Social]  
[A/C — Gerente de Contas / Suporte Técnico]

**Assunto:** Solicitação de acesso à API 1Doc para integração com o sistema de gestão patrimonial do [IPMJP].

**Referências:**
- Contrato/[nº do processo administrativo] de fornecimento do sistema 1Doc ao [IPMJP];
- Processo Administrativo nº [XXXX/2026] — [objeto];
- Programa de gestão patrimonial do [IPMJP] — [SisPatrimônio Pro].

---

Senhor(a) [nome, se conhecido],

1. O [Instituto/Fundação de Previdência dos Servidores do Município de João Pessoa — IPMJP], órgão cliente do sistema 1Doc, vem desenvolvendo a automação do registro de suas movimentações patrimoniais — cautela/entrega de equipamentos a servidores e transferências entre locais — por meio do sistema [SisPatrimônio Pro].

2. O fluxo administrativo adotado pelo setor de Patrimônio prevê que cada movimentação seja comunicada em **processo administrativo 1Doc previamente criado pelo próprio setor**, contendo mensagem padronizada com os dados da operação, conforme o modelo atualmente utilizado:

   > Bom dia! Seguem os dados acerca da movimentação do equipamento:
   >
   > | Descrição do Material | Tombamento | Origem | Destino |
   > |---|---|---|---|
   > | Monitor DELL | 0008 | Suporte | Desenvolvimento |

3. Objetiva-se, portanto, por meio da API disponibilizada ao órgão, **incluir automaticamente essa comunicação no processo 1Doc existente** no momento em que a movimentação é registrada. Registra-se expressamente que **não se pretende criar novos processos, substituir fluxos internos do 1Doc nem interferir no fluxo de assinatura** — o documento administrativo e a assinatura do responsável permanecem integralmente no ambiente do 1Doc.

4. Para dimensionar a integração estritamente pelas capacidades **efetivamente disponibilizadas** à instalação do IPMJP, solicita-se a gentileza de encaminhar as informações a seguir.

   **4.1 Autenticação**
   a) Método de autenticação da API (API key, token Bearer, OAuth2);
   b) Validade da credencial e procedimento de renovação/revogação;
   c) Existência de escopos ou perfis de acesso distintos (leitura × escrita).

   **4.2 Consulta de processo**
   a) Possibilidade de localizar/consultar um processo pelo número conhecido do usuário;
   b) *Endpoint* correspondente e dados retornados (identificador interno, status, dados básicos).

   **4.3 Validação de existência do processo**
   a) Possibilidade de confirmar a existência de um processo **antes** da inclusão de comunicação (consulta leve ou retorno específico para número inexistente).

   **4.4 Inclusão de comunicação no processo**
   a) *Endpoint* para adicionar nova comunicação/mensagem a um processo existente;
   b) Formatos de conteúdo aceitos: texto puro, HTML, tabela ou somente modelos/templates pré-configurados;
   c) Possibilidade de anexar arquivos à comunicação (não essencial na primeira versão);
   d) Retorno de um **identificador da mensagem criada**.

   **4.5 Formato do número de processo**
   a) Convenção real do número de processo no ambiente do IPMJP (ex.: `2026/000123`, `000123/2026`, sequencial sem barra);
   b) Regras de validação da entrada: caracteres permitidos, tamanho, uso de barras/traços, caixa alta/baixa.

   **4.6 Informações complementares**
   a) Mecanismo nativo de idempotência (chave de idempotência) para prevenção de mensagens duplicadas em caso de reenvio;
   b) Códigos de erro comuns e eventuais limites de taxa (*rate limits*);
   c) Existência de **ambiente de homologação/teste** com credenciais próprias;
   d) Possibilidade de designar signatário/encaminhar para assinatura via API (a assinatura seguirá no fluxo normal do 1Doc; o item destina-se apenas ao registro documental da capacidade).

5. Solicita-se, ainda, o envio da **documentação oficial da API** (referência de *endpoints* e, se disponível, especificação *Swagger*/OpenAPI), bem como as **credenciais de acesso** para o ambiente do órgão.

6. Para fins de planejamento técnico, informa-se que o servidor da aplicação encontra-se no endereço IP `10.39.0.16` (rede interna do órgão) e a integração utilizará comunicação HTTP/REST padrão. A equipe técnica do IPMJP permanece à disposição para reunião de alinhamento, caso se faça necessário.

7. Agradecendo desde já a atenção dispensada, renovo os protestos de estima e consideração.

[Local], [dia] de [mês] de 2026.

<br>

**[Nome completo]**  
[Cargo] — [Setor de Patrimônio]  
[IPMJP — Instituto/Fundação de Previdência dos Servidores do Município de João Pessoa]  
Telefone: [XX XXXXX-XXXX] · E-mail: [e-mail institucional]

---

## Notas internas (não enviar)

- Copiar o conteúdo do ofício para papel timbrado do órgão antes do envio protocolar;
- O número do ofício ([XXX]/2026) deve seguir a sequência do setor — ajustar antes de protocolar;
- Referências (processo administrativo/contrato): preencher conforme o contrato vigente do 1Doc;
- **Pergunta 4.5 (formato do número)** destrava a validação FR-002/analyze U1 — hoje o sistema aceita qualquer texto com trim (`process_number`, String(60)) por não conhecermos a convenção;
- **Item 4.6-c (homologação)** permite testar a integração real sem tocar em processos administrativos verdadeiros (quickstart §5 da feature 031);
- Mapeamento respostas → código: (4.1)→header de auth em `onedoc_client.py` `[PENDING C-1]`; (4.2)/(4.3)→`find_process` `[PENDING C-2/C-3]` (define modo bloqueante × tolerante da decisão Q2); (4.4)→`send_communication` `[PENDING C-4]` (escolhe texto vs HTML); (4.6-a)→reforço da UNIQUE `movement_id` (C-6); (4.6-d)→documentação da limitação (C-5, fora de escopo v1);
- Após as respostas: conectar os pontos `[PENDING C-1..C-4]`, rodar o quickstart §5 (validação real) e somente então `ONEDOC_ENABLED=true` em produção.
