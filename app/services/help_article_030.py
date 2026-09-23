"""Artigo da central de ajuda — Notificações por e-mail (feature 030).

Importado por help_service e inserido na lista de artigos de administração,
seguindo exatamente o schema dos artigos existentes (id/title/module/icon/
audience/summary/keywords/sections).
"""

ARTIGO_NOTIFICACOES = {
    "id": "notificacoes-email",
    "title": "Notificações por e-mail de movimentações (administração)",
    "module": "Notificações",
    "icon": "bi-envelope-check",
    "audience": "admin",
    "summary": "Ativar/desativar o aviso automático por e-mail ao setor de Patrimônio após movimentações (entrega/cautela, transferência e devolução) e configurar os destinatários.",
    "keywords": [
        "notificações", "e-mail", "email", "patrimônio", "movimentação",
        "destinatários", "cautela", "transferência", "devolução", "aviso",
        "ciência", "smtp", "configuração", "admin",
    ],
    "sections": [
        {
            "heading": "O que a notificação faz",
            "body": (
                "Quando uma movimentação patrimonial é concluída — entrega/cautela "
                "(Alocação / Cautela), Transferência de Local ou Devolução ao Estoque — "
                "o sistema envia automaticamente um e-mail aos destinatários configurados "
                "(ex.: a caixa do setor de Patrimônio), com os dados da operação: "
                "tombamento, identificação do bem, tipo de movimentação, local e "
                "responsável de origem/destino, data/hora e o usuário que realizou. "
                "Demais tipos de movimentação (aquisição, manutenção, baixa, ajuste) "
                "e a importação em lote de CSV não geram e-mail nesta versão."
            ),
        },
        {
            "heading": "Como configurar",
            "body": (
                "Acesse Administração → Notificações (requer a permissão notificacoes.gerenciar). "
                "Ative a notificação, informe um ou mais e-mails de destino (um por linha ou "
                "separados por vírgula) e salve — a alteração vale na hora, sem reiniciar o "
                "sistema. Ativar exige pelo menos um destinatário válido. Com as notificações "
                "desativadas, nenhuma movimentação gera e-mail — este é o comportamento padrão "
                "até a ativação explícita."
            ),
        },
        {
            "heading": "Servidor de e-mail (SMTP)",
            "body": (
                "O remetente e a conexão de envio são definidos pelo administrador do "
                "SERVIDOR nas variáveis SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, "
                "SMTP_FROM, SMTP_USE_TLS e SMTP_SEND_TIMEOUT do arquivo .env — nunca pela tela. "
                "A senha SMTP é segredo do servidor: não aparece na interface, no banco nem na auditoria."
            ),
        },
        {
            "heading": "Se o envio falhar",
            "body": (
                "A falha de e-mail NUNCA afeta a movimentação: a operação patrimonial permanece "
                "concluída e o operador não vê erro. A falha fica registrada na trilha de "
                "auditoria (ação \"Notificação Falhou\", com os destinatários e o motivo técnico "
                "sem dados sensíveis) para ciência posterior do administrador. Cada movimentação "
                "gera no máximo um e-mail — mesmo em reprocessos, não há duplicidade."
            ),
        },
        {
            "heading": "Importante",
            "note": (
                "O e-mail é um mecanismo de ciência/aviso institucional: não exige ação e não "
                "contém link de consulta nesta versão. A auditoria da notificação exige a "
                "permissão auditoria.visualizar para consulta. A configuração exige a permissão "
                "notificacoes.gerenciar."
            ),
        },
    ],
}
