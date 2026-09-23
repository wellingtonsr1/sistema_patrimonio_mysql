"""Artigo da central de ajuda — Integração 1Doc (feature 031).

Importado por help_service e inserido na lista de artigos de administração,
seguindo exatamente o schema dos artigos existentes (id/title/module/icon/
audience/summary/keywords/sections) — precedente help_article_030.
"""

ARTIGO_ONEDOC = {
    "id": "integracao-1doc",
    "title": "Integração 1Doc (administração)",
    "module": "Integração 1Doc",
    "icon": "bi-file-earmark-text",
    "audience": "admin",
    "summary": "Inclusão automática da comunicação de movimentação no processo 1Doc do setor de Patrimônio, com tabela preenchida pelos dados oficiais; reprocessamento de falhas.",
    "keywords": [
        "1doc", "integração", "processo", "comunicação", "movimentação",
        "cautela", "transferência", "reprocessar", "falha", "patrimônio",
        "admin", "processo administrativo", "assinatura",
    ],
    "sections": [
        {
            "heading": "O que a integração faz",
            "body": (
                "Quando uma movimentação elegível é concluída — Alocação / Cautela ou "
                "Transferência de Local — e o operador informa o número do processo 1Doc "
                "no formulário, o sistema inclui automaticamente uma comunicação nesse "
                "processo, com a mensagem no modelo do setor de Patrimônio (saudação + "
                "tabela com Descrição do Material, Tombamento, Origem e Destino). O "
                "responsável pela movimentação assina no próprio 1Doc, pelo fluxo já "
                "utilizado pelo órgão. Demais tipos (devolução, manutenção, baixa, "
                "ajuste, aquisição) não interagem com o 1Doc."
            ),
        },
        {
            "heading": "Informar o processo 1Doc",
            "body": (
                "O campo 'Processo 1Doc' aparece somente nos formulários de cautela e "
                "transferência (e somente com a integração ativada). O processo deve já "
                "existir — ele é criado pelo setor de Patrimônio; o sistema não cria "
                "processos. Com a integração ativa, concluir uma cautela ou transferência "
                "sem informar o processo não é permitido. Se a API do 1Doc permitir "
                "consulta, um processo inexistente é rejeitado antes de gravar a "
                "movimentação; sem esse suporte, o número é aceito e qualquer problema "
                "vira uma falha registrada, recuperável por reprocessamento."
            ),
        },
        {
            "heading": "Falhas e reprocessamento",
            "body": (
                "Se o 1Doc estiver indisponível, a movimentação permanece válida — nada "
                "é desfeito. A tentativa fica registrada como 'Falhou' (com o motivo "
                "técnico, sem dados sensíveis) e pode ser reenviada na tela "
                "Administração → Integração 1Doc pelo botão 'Reprocessar'. O acesso a "
                "essa tela exige a permissão 'Reprocessar integração 1Doc' "
                "(integracao1doc.reprocessar), concedida por um administrador a quem "
                "operará a integração — ninguém a recebe automaticamente. Reprocessar "
                "não duplica comunicações: cada movimentação gera no máximo uma "
                "comunicação no processo."
            ),
        },
        {
            "heading": "Auditoria e privacidade",
            "body": (
                "Todos os eventos ficam na trilha de auditoria: Integração 1Doc "
                "Solicitada / Enviada / Falhou (automáticos) e Reprocessada (com o "
                "usuário que acionou). Nenhum evento contém token ou credenciais. O "
                "e-mail de notificação do setor (feature 030) continua funcionando "
                "independentemente desta integração."
            ),
        },
    ],
}
