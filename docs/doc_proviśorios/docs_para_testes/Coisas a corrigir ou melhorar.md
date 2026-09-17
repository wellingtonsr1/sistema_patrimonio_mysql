1 - Implementar o reset de senha do admin ---> OK
1.1 Atuzalizar "Ajuda/Manual" + docuemntação ---> OK

2 - Na conferência do inventário: "Resultado da conferência: LOCAL DIFERENTE de: Situação da divergência: PENDENTE DE REGULARIZAÇÃO" ---> OK
Depois poderia evoluir para:

LOCAL DIFERENTE
        ↓
DIVERGÊNCIA PENDENTE
        │
        ├── Bem deve voltar ao RH
        │       ↓
        │   REGULARIZADA
        │
        └── Bem deve ficar no TI
                ↓
          Movimentação RH → TI
                ↓
            REGULARIZADA
Em resumo: o sistema já armazena a divergência, mas pelo código enviado não há ainda um status específico para acompanhar a regularização dela. Esse seria um possível aprimoramento do módulo, caso você queira controlar o ciclo divergente → tratado → regularizado.

Fluxo de movimentações:
| Local     | Responsável | Tipo                                                                     |
| --------- | ----------- | ------------------------------------------------------------------------ |
| igual     | igual       | ❌ Bloquear                                                               |
| igual     | diferente   | ✅ Alocação / Cautela                                                     |
| diferente | igual       | ✅ Transferência de Setor / Filial                                        |
| diferente | diferente   | ✅ Alocação / Cautela, se for entrega ao novo colaborador                 |
| estoque   | colaborador | ✅ Alocação / Cautela                                                     |
| estoque   | nenhum      | depende da operação; não deve ser uma alocação concluída sem responsável |
2.1 Atuzalizar "Ajuda/Manual" + docuemntação

3 - Problema das matrículas: ---> OK
Para o SisPatrimônio, há uma alternativa melhor: gerar um identificador provisório claramente marcado, por exemplo:

PROV-000001
PROV-000002
PROV-000003

ou:

TEMP-000001
TEMP-000002

Assim fica impossível confundir com uma matrícula funcional verdadeira.
Eu colocaria algumas regras

1. Prefixo obrigatório

PROV-

2. Número gerado automaticamente

Nunca permitir que o usuário escolha:

PROV-000123

para evitar duplicidade.

3. Identificador provisório não pode ser confundido com matrícula oficial

Na tela poderia aparecer:

Matrícula: PROV-000123 (provisória)

4. Não permitir duas pessoas com o mesmo identificador.

5. Permitir posteriormente informar a matrícula oficial.

6. Não usar CPF, telefone, AD username ou outro dado pessoal como matrícula fictícia.

4 - Decidir se coloca exporta pdf. cvs, excel ou Ajusta a impressão
4.1 Atuzalizar "Ajuda/Manual" + docuemntação

5 - ajustar impressão em Trilha de Auditoria & Fluxo, Relação de Colaboradores & Custodiantes ---> OK
5.1 Atuzalizar "Ajuda/Manual" + docuemntação

6 - Ajustar impressão em relatórios ---> OK
6.1 Atuzalizar "Ajuda/Manual" + docuemntação

7 - risco de sobrescrita silenciosa: ---> OK
Fluxo do usuário na prática

```text
Conferente B abre o modal de um item já conferido por A
      ↓
Vê o alerta: "Já conferido por Maria Souza em 12/09 14:32 — Encontrado"
      ↓
Confere no campo e decide:
   ├─ resultado de B é igual → não precisa registrar nada (evita sobrescrita à toa)
   └─ resultado diverge → marca novo resultado → confirm() "vai substituir" → OK
      ↓
POST /inventarios/{id}/conferir/{item_id} (rota e service intactos)
      ↓
Sobrescrita gravada + auditoria com antes/depois (quem, quando, IP)
      ↓
Ata final continua imutável após o encerramento
7.1 Atuzalizar "Ajuda/Manual" + docuemntação

8 - Ver correção da hora ---> OK

9 - Na importação, nao fica o nome de quem já tá cadastrado

10 - Campo para pesqusia de colaborador ---> OK

11 - Campo para pesqusia de local ---> OK

12 - Ajustar a cor do check da tela de conferência.

13 - Colocar 'Departamento / Setor' exibindo a lista ---> OK