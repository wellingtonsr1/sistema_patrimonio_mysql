"""Artigo da Central de Ajuda — Central de Integrações (feature 032).

Padrão help_article_030/help_article_031: conteúdo concentrado, importado
por `help_service` e integrado à Central de Ajuda (/ajuda).
"""
from typing import Dict

ARTIGO_CENTRAL_INTEGRACOES: Dict = {
    "id": "central-de-integracoes",
    "title": "Central de Integrações",
    "module": "Administração",
    "icon": "bi-diagram-3",
    "audience": "admin",
    "summary": "Painel com o estado das integrações do sistema (E-mail, 1Doc, GLPI, Active Directory): status, diagnóstico, teste de conexão, histórico de execuções e propagação por movimentação.",
    "keywords": [
        "central", "integrações", "integração", "e-mail", "email", "1doc", "glpi",
        "active directory", "ad", "status", "teste de conexão", "histórico",
        "reprocessar", "propagação", "movimentação", "segredos", "credenciais",
    ],
    "sections": [
        {
            "heading": "O que é",
            "body": (
                "A Central de Integrações é a área de Administração que reúne, em um único lugar, o estado "
                "das integrações do SisPatrimônio Pro. Ela não substitui as telas de configuração existentes "
                "(Notificações, Integração AD, Integração 1Doc): funciona como camada de acompanhamento sobre "
                "o que já existe.\n\n"
                "Com ela você responde rapidamente: quais integrações existem, qual está com problema, desde "
                "quando, quantas operações foram afetadas, se há operações pendentes e se a conexão está "
                "funcionando agora."
            ),
        },
        {
            "heading": "Quem pode acessar",
            "body": (
                "O menu Administração → Central de Integrações aparece apenas para usuários com a permissão "
                "'Visualizar Central de Integrações' (integracoes.visualizar). Executar o 'Testar conexão' do "
                "e-mail e do 1Doc exige a permissão 'Testar conexões de integrações' (integracoes.testar). As "
                "ações específicas continuam exigindo as permissões de sempre: reprocessar 1Doc "
                "(integracao1doc.reprocessar), tela AD (usuarios.editar + perfis.editar) e tela Notificações "
                "(notificacoes.gerenciar)."
            ),
        },
        {
            "heading": "Status das integrações",
            "steps": [
                "Não Configurada — faltam parâmetros mínimos ou a integração ainda não foi implementada (ex.: GLPI).",
                "Pendente de Configuração — aguardando algo externo (ex.: 1Doc aguardando o fornecedor).",
                "Desabilitada — implementada, mas explicitamente desligada (ex.: notificações desativadas).",
                "Ativa — habilitada e operando.",
                "Com Erro — a última execução/verificação falhou.",
                "Indisponível — serviço externo não alcançável no momento (rede/timeout).",
                "Inativa — habilitada, porém sem atividade registrada.",
            ],
        },
        {
            "heading": "O que cada card mostra",
            "steps": [
                "Última execução e último sucesso da integração.",
                "Falhas recentes nas últimas 24 horas (janela explícita no card).",
                "Operações pendentes (ex.: comunicações 1Doc aguardando envio).",
                "Botões: Detalhes, Testar conexão (quando suportado) e Configurar (tela existente).",
            ],
        },
        {
            "heading": "Testar conexão",
            "body": (
                "O teste é seguro e não destrutivo: no e-mail, apenas abre conexão e autentica no servidor "
                "SMTP — nenhuma mensagem é enviada. No 1Doc, verifica apenas a configuração interna (o envio "
                "real permanece bloqueado até a confirmação do contrato pelo fornecedor). O teste do Active "
                "Directory continua na tela Integração AD, como sempre. Todo teste fica registrado no histórico "
                "e na trilha de auditoria."
            ),
            "note": "O teste nunca cria, altera ou exclui dados no sistema externo nem no acervo patrimonial.",
        },
        {
            "heading": "Histórico e propagação",
            "body": (
                "Cada integração possui histórico de execuções (data/hora, operação, resultado, duração e "
                "detalhes) com filtros por período, status, operação e usuário. A consulta de propagação "
                "(por movimentação) mostra se a movimentação foi propagada aos sistemas externos: e-mail "
                "enviado, comunicação 1Doc pendente, GLPI não aplicável — permitindo acionar o reprocessamento "
                "pela tela existente quando necessário."
            ),
        },
        {
            "heading": "Segurança das credenciais",
            "body": (
                "Nenhuma credencial é exibida na Central: segredos aparecem apenas como indicação de "
                "configurado (com máscara), nunca o valor. As credenciais continuam vivendo exclusivamente "
                "nas variáveis de ambiente do servidor (SMTP_PASSWORD, ONEDOC_API_TOKEN, AD_BIND_PASSWORD) — "
                "configuradas no .env, fora do banco e fora da interface."
            ),
        },
    ],
}
