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
    "summary": "Painel com o estado do sistema e das integrações (Aplicação, Banco de Dados, Armazenamento, Active Directory, E-mail, GLPI, Backup Local, Backup Externo, Agendador de Backup e 1Doc): status, diagnóstico, teste de conexão, histórico de execuções e propagação por movimentação.",
    "keywords": [
        "central", "integrações", "integração", "e-mail", "email", "1doc", "glpi",
        "active directory", "ad", "status", "teste de conexão", "histórico",
        "reprocessar", "propagação", "movimentação", "segredos", "credenciais",
        "saúde", "aplicação", "banco de dados", "armazenamento", "backup",
        "backup local", "backup externo", "agendador", "backup automático",
    ],
    "sections": [
        {
            "heading": "O que é",
            "body": (
                "A Central de Integrações é a área de Administração que reúne, em um único lugar, o estado "
                "do sistema e das integrações do SisPatrimônio Pro. Ela não substitui as telas de configuração "
                "existentes (Notificações, Integração AD, Integração 1Doc, Backups): funciona como camada de "
                "acompanhamento sobre o que já existe.\n\n"
                "Com ela você responde rapidamente: se a aplicação está operacional, se o banco de dados responde, "
                "se o armazenamento está adequado, se o Active Directory está acessível, se o e-mail está "
                "configurado, se o backup local está funcionando, se o backup externo está acessível, se o "
                "agendador de backup está ativo, quais integrações estão configuradas, não configuradas ou com "
                "falha — e qual está com problema, desde quando, quantas operações foram afetadas, se há "
                "operações pendentes e se a conexão está funcionando agora."
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
            "heading": "Componentes monitorados",
            "steps": [
                "Aplicação — o próprio carregamento da Central comprova que o sistema responde.",
                "Banco de Dados — verificado pela mesma conexão do sistema (sem conexão nova).",
                "Armazenamento — espaço livre nos diretórios de backup; Atenção quando o espaço livre fica abaixo do tamanho do último backup válido.",
                "Active Directory — configurado/habilitado e resultado do último teste (teste completo na tela Integração AD).",
                "E-mail — configurado/não configurado e último teste de conexão SMTP.",
                "GLPI — integração prevista: permanece Não Configurada até a implementação.",
                "Backup Local — último backup válido, quantidade de backups válidos no disco e última falha; com agendador ativo, Atenção quando o ciclo esperado passa sem backup novo.",
                "Backup Externo — habilitado, destino, última cópia e última falha (feature 045).",
                "Agendador de Backup — ativo/desabilitado, agendamento, próximo backup e último resultado.",
                "1Doc — comunicação de movimentações; Pendente de Configuração enquanto o contrato não é confirmado pelo fornecedor.",
            ],
        },
        {
            "heading": "Status das integrações",
            "steps": [
                "Não Configurada — faltam parâmetros mínimos ou a integração ainda não foi implementada (ex.: GLPI).",
                "Pendente de Configuração — aguardando algo externo (ex.: 1Doc aguardando o fornecedor).",
                "Desabilitada — implementada, mas explicitamente desligada (ex.: notificações desativadas, backup externo desligado).",
                "Ativa — habilitado e operando (nos componentes de saúde, exibido como Operacional/Conectado/OK/Ativo).",
                "Atenção — configurado com ressalva (ex.: pouco espaço de armazenamento, backup atrasado).",
                "Com Erro — a última execução/verificação falhou.",
                "Indisponível — serviço externo não alcançável no momento (rede/timeout).",
                "Inativa — habilitado, porém sem atividade registrada.",
            ],
        },
        {
            "heading": "O que cada card mostra",
            "steps": [
                "Última execução e último sucesso da integração.",
                "Falhas recentes nas últimas 24 horas (janela explícita no card).",
                "Operações pendentes (ex.: comunicações 1Doc aguardando envio).",
                "Resumo operacional de uma linha por componente (ex.: próximo backup, último backup válido, espaço livre, destino externo).",
                "Botões: Detalhes, Testar conexão/Testar destino (quando suportado) e Configurar (tela existente).",
            ],
        },
        {
            "heading": "Testar conexão",
            "body": (
                "O teste é seguro e não destrutivo: no e-mail, apenas abre conexão e autentica no servidor "
                "SMTP — nenhuma mensagem é enviada. No 1Doc, verifica apenas a configuração interna (o envio "
                "real permanece bloqueado até a confirmação do contrato pelo fornecedor). No Backup Externo, "
                "o 'Testar destino' cria um arquivo temporário, grava, lê, valida e remove — nenhum backup é "
                "gerado e nenhum arquivo fica no destino. O teste do Active Directory continua na tela "
                "Integração AD, como sempre. Abrir a Central apenas CONSULTA estados já conhecidos: nenhum "
                "teste é executado automaticamente ao carregar a página. Todo teste fica registrado no "
                "histórico e na trilha de auditoria."
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
