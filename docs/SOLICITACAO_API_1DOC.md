# Solicitação ao Fornecedor 1Doc — Acesso à API (Feature 031)

**Data**: 2026-09-23
**Origem**: Feature 031 (Integração 1Doc) — pendência externa Fase 1 (itens C-1..C-8 da spec `specs/031-integracao-1doc/spec.md`)
**Status**: Rascunho para envio — preencher os campos entre colchetes

---

**Assunto:** Solicitação de acesso à API 1Doc — integração com sistema de patrimônio do [IPMJP]

Prezados,

Sou [seu nome / cargo], responsável pelo [SisPatrimônio Pro / setor] no [IPMJP — Instituto/Fundação de Previdência dos Servidores de João Pessoa], órgão cliente do 1Doc.

Estamos automatizando o registro de movimentações patrimoniais (cautela/entrega de equipamentos e transferências de local) e gostaríamos de **incluir uma comunicação em um processo 1Doc já existente**, criado previamente pelo nosso setor de Patrimônio, contendo a mensagem que já utilizamos hoje, por exemplo:

> Bom dia! Seguem os dados acerca da movimentação do equipamento:
>
> | Descrição do Material | Tombamento | Origem | Destino |
> |---|---|---|---|
> | Monitor DELL | 0008 | Suporte | Desenvolvimento |

Ou seja: **não pretendemos criar processos nem substituir fluxos internos do 1Doc** — apenas apendar essa comunicação ao processo, via API, no momento em que a movimentação é registrada no nosso sistema. Para dimensionar a integração com o que a API **efetivamente** disponibiliza à nossa instalação, precisamos das informações abaixo:

## 1. Autenticação

- Qual o método de autenticação da API (API key, token Bearer, OAuth2)?
- Qual a validade da credencial e o processo de renovação/revogação?
- Há escopos/perfis de acesso distintos (leitura × escrita)?

## 2. Consulta de processo

- A API permite **localizar/consultar um processo pelo número** conhecido pelo usuário?
- Se sim, qual o *endpoint* e o que a consulta retorna (identificador interno do processo, status, dados básicos)?

## 3. Validação de existência do processo

- A API permite **confirmar a existência de um processo antes** de incluir uma comunicação (ex.: consulta leve ou retorno específico para número inexistente)?

## 4. Inclusão de comunicação no processo

- Qual o *endpoint* para **adicionar uma nova comunicação/mensagem** a um processo existente?
- Quais **formatos de conteúdo** são aceitos: texto puro, HTML, tabela, ou somente modelos/templates pré-configurados?
- É possível **anexar arquivos** à comunicação (não é essencial na primeira versão)?
- A resposta retorna um **identificador da mensagem criada**?

## 5. Formato do número de processo

- Qual a **convenção real** do número de processo no ambiente do IPMJP (ex.: `2026/000123`, `000123/2026`, número sequencial sem barra)? Precisamos para validar a entrada no nosso sistema (caracteres permitidos, tamanho, uso de barras/traços, maiúsculas/minúsculas).

## 6. Informações complementares (se houver documentação de fácil acesso)

- A API oferece mecanismo nativo de **idempotência** (chave de idempotência) para evitar mensagens duplicadas em caso de reenvio?
- Quais os **códigos de erro** mais comuns e há limites de taxa (*rate limits*)?
- Existe **ambiente de homologação/teste** com credenciais próprias para desenvolvermos sem tocar em processos reais?
- A API permite **designar signatário/encaminhar para assinatura**? *(A assinatura seguirá no fluxo normal do 1Doc — é apenas para documentarmos a capacidade.)*

Em paralelo, solicitaríamos a **documentação oficial da API** (referência de endpoints, *Swagger*/OpenAPI, se houver) e as **credenciais de acesso** para o nosso ambiente.

**Nossos dados técnicos**: servidor da aplicação no IP `10.39.0.16` (rede interna do órgão), integração em linguagem de servidor (HTTP/REST). Podemos ajustar qualquer detalhe em reunião rápida, se preferirem.

Desde já agradeço; ficamos no aguardo.

Atenciosamente,
[Nome completo]
[Cargo — Setor]
[IPMJP] · [telefone] · [e-mail]

---

## Notas internas (não enviar)

- **Pergunta 5 (formato do número)** é a que destrava a validação FR-002/analyze U1 — hoje o sistema aceita qualquer texto com trim (`onedoc_integrations.process_number`, String(60)) justamente por não conhecermos a convenção;
- **Pergunta 6 (homologação)** permite testar a integração real sem tocar em processos administrativos verdadeiros (quickstart §5 da feature 031);
- Mapeamento respostas → código: (1)→header de auth em `onedoc_client.py` `[PENDING C-1]`; (2)/(3)→`find_process` `[PENDING C-2/C-3]` (define modo bloqueante × tolerante da decisão Q2); (4)→`send_communication` `[PENDING C-4]` (escolhe texto vs HTML); (6-idempotência)→reforço da UNIQUE `movement_id` (C-6); (6-assinatura)→documentação da limitação (C-5, fora de escopo v1);
- Após as respostas: conectar os pontos `[PENDING C-1..C-4]`, rodar quickstart §5 (validação real) e só então `ONEDOC_ENABLED=true` em produção.
