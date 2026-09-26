"""Artigo da Central de Ajuda — Destino externo de backups (feature 045).

Padrão help_article_030/help_article_031/help_article_032: conteúdo
concentrado, importado por `help_service` e integrado à Central de Ajuda
(/ajuda).
"""
from typing import Dict

ARTIGO_BACKUP_EXTERNO: Dict = {
    "id": "backup-destino-externo",
    "title": "Backup com destino externo (pasta de rede/NAS)",
    "module": "Administração",
    "icon": "bi-hdd-network",
    "audience": "admin",
    "summary": "Copiar automaticamente cada backup local válido para uma pasta de rede/NAS montada no servidor: ativar, informar o destino, testar e acompanhar o resultado na tela de Backups.",
    "keywords": [
        "backup", "externo", "destino externo", "nas", "pasta de rede", "cópia externa",
        "copia externa", "montada", "mount", "redundância", "sha-256", "testar destino",
        "configurações", "engrenagem", "histórico", "auditoria",
    ],
    "sections": [
        {
            "heading": "O que faz",
            "body": (
                "Com o destino externo ativado, todo backup local válido do sistema — manual, automático "
                "(no horário agendado) e o pré-restauração (gerado antes de cada restauração) — passa por "
                "uma segunda cópia automática para uma pasta de rede ou NAS já montada no servidor.\\n\\n"
                "A cópia só é considerada bem-sucedida se o arquivo chegar completo e com o mesmo SHA-256 "
                "do original. A pasta local de backups (data/backups) continua sendo sempre gerada primeiro: "
                "o externo é uma camada adicional de proteção, nunca um substituto."
            ),
        },
        {
            "heading": "O que precisa existir antes (infraestrutura)",
            "steps": [
                "Uma pasta compartilhada na máquina/NAS de destino (ex.: servidor de arquivos da rede).",
                "Essa pasta montada no servidor da aplicação em um caminho local (ex.: /mnt/backup-sispatrimonio) — a montagem é configuração do servidor, feita pelo administrador de infraestrutura (NFS/SMB; persistida no /etc/fstab para sobreviver a reinícios).",
                "Permissão de escrita na pasta para o usuário do processo da aplicação.",
            ],
            "note": (
                "O sistema não monta discos, não informa credenciais e não cria a pasta de destino: por "
                "segurança, a pasta é infraestrutura do servidor. O campo de configuração recebe apenas o "
                "caminho já montado (caminho absoluto, sem acentos). Guia completo de montagem e permissões: "
                "docs/TUTORIAL_BACKUP_DESTINO_EXTERNO.md."
            ),
        },
        {
            "heading": "Como ativar e testar",
            "steps": [
                "Acesse Administração → Backups.",
                "Clique no botão de engrenagem (canto superior direito) para abrir o modal Configurações de Backup.",
                "No quadro Backup externo, ligue a chave Cópia externa ativada (fica desmarcada por padrão — o sistema só copia quando você ativa).",
                "No campo Destino, informe o caminho montado no servidor (ex.: /mnt/backup-sispatrimonio). O tipo é fixo: Pasta de rede/NAS.",
                "Clique em Testar destino — o teste cria, lê e remove um pequeno arquivo temporário no destino, sem gerar backup; o resultado aparece no topo da página.",
                "Clique em Salvar configuração (salva junto com agendamento e retenção do mesmo formulário).",
            ],
        },
        {
            "heading": "Resultados do Testar destino",
            "steps": [
                "\"Destino acessível: escrita, leitura e remoção OK.\" — pode salvar.",
                "\"O destino informado não existe ou não é um diretório.\" — o caminho não existe no servidor (montagem inativa ou caminho digitado errado).",
                "\"Sem permissão de escrita no destino.\" — a pasta existe, mas o usuário da aplicação não pode gravar nela.",
            ],
            "note": "O teste e o salvamento exigem a permissão backup.gerenciar — a mesma de sempre; nenhuma permissão nova foi criada.",
        },
        {
            "heading": "Como acompanhar na tela de Backups",
            "steps": [
                "Card Destino externo — mostra se está ativado, o caminho configurado, a última cópia/tentativa e o último resultado (SUCESSO/FALHA com o motivo). Antes da primeira cópia, mostra \"Nenhuma ainda\".",
                "Coluna Externo no histórico — ✓ para os backups copiados com sucesso; ✗ para tentativa que falhou (passe o mouse para ver o motivo); — para backups sem cópia (anteriores à ativação).",
                "Ao gerar um backup manual, a mensagem confirma as duas etapas: \"Backup local: SUCESSO (arquivo) / Backup externo: SUCESSO\" — ou \"... / Backup externo: FALHA (motivo)\".",
            ],
        },
        {
            "heading": "Motivos de falha e o que fazer",
            "steps": [
                "Destino indisponível — a pasta montada não está acessível (servidor de arquivos desligado, montagem perdida após reinício). Reaqueça a montagem ou verifique a rede; a cópia é re-tentada no próximo backup.",
                "Sem permissão de escrita — revise as permissões da pasta no destino.",
                "Espaço insuficiente no destino — libere espaço ou amplie o volume; a retenção do sistema NÃO apaga nada no destino.",
                "Falha de integridade (sha256 divergente) — o arquivo no destino divergiu do original; investigue e remova o arquivo divergente para permitir nova cópia.",
                "Tempo limite da cópia — arquivo grande ou rede lenta; o sistema tenta novamente no próximo ciclo.",
            ],
            "note": (
                "Uma falha externa NUNCA invalida o backup local: ele permanece íntegro e disponível. A falha "
                "aparece no card, na coluna Externo e na auditoria. Toda cópia é atômica: só existe arquivo "
                "com o nome definitivo no destino depois de copiado e validado por completo (nunca um parcial)."
            ),
        },
        {
            "heading": "Retenção e limpeza",
            "body": (
                "A política de retenção do sistema atua apenas sobre os backups locais (data/backups). O "
                "destino externo nunca é varrido nem limpo pela aplicação: as cópias se acumulam até que o "
                "administrador faça a limpeza operacional (manualmente, na pasta/NAS). Combine uma rotina de "
                "limpeza conforme o espaço disponível."
            ),
        },
        {
            "heading": "Auditoria",
            "body": (
                "Quatro eventos novos na trilha (módulo Backup): configuração salva com alteração "
                "(Destino Externo de Backup Configurado), execução do teste (Destino Externo de Backup "
                "Testado), cópia validada (Backup Externo Realizado) e cópia falhada (Backup Externo "
                "Falhou, com o motivo). Nenhum evento contém credenciais — o mecanismo não manipula "
                "segredos."
            ),
        },
    ],
}
