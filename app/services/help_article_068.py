"""Artigo da Central de Ajuda — Paginação de listas e integridade de relatórios/exportações (feature 068).

Padrão help_article_030/help_article_031/help_article_032: conteúdo
concentrado, importado por `help_service` e integrado à Central de Ajuda
(/ajuda).

Documenta para o usuário:
- listas paginadas por página (page size 200 fixo), com total e controles
  Anterior/Próxima e indicador "Mostrando X-Y de Z";
- relatórios (inventário e trilha de movimentações) paginados com total real;
- exportações CSV/XLSX/PDF íntegras ou explicitamente avisadas (nenhum corte
  silencioso).
"""
from typing import Dict

ARTIGO_PAGINACAO_RELATORIOS: Dict = {
    "id": "paginação-e-relatórios",
    "title": "Paginação nas listas e relatórios",
    "module": "Navegação & Relatórios",
    "icon": "bi-book",
    "audience": "user",
    "summary": "Como encontrar registros além da primeira página e confiar nos relatórios/exportações.",
    "keywords": [
        "paginação", "page", "página", "anterior", "próxima", "total",
        "relatório", "exportar", "CSV", "Excel", "PDF", "corte", "exportação completa",
        "inventário", "trilha", "movimentações",
    ],
    "sections": [
        {
            "heading": "Listas paginadas",
            "body": (
                "As listas do sistema (Equipamentos, Movimentações, Colaboradores, "
                "Locais, Inventários, Itens de inventário e Trilha de Auditoria) "
                "são navegáveis por páginas de 200 registros. Abaixo da lista, o "
                "controle de página exibe o intervalo corrente e o total do filtro "
                "(Mostrando X-Y de Z), com os botões Anterior e Próxima.\n\n"
                "Se o filtro retornar poucos registros e couber em uma única página, "
                "o controle de página não é exibido (para não poluir a tela). "
                "Os filtros, busca e status que você aplicou permanecem aplicados "
                "ao trocar de página — a URL completa including os filtros pode ser "
                "compartilhada e chega ao destinatário exatamente onde você estava."
            ),
        },
        {
            "heading": "Como navegar entre páginas",
            "steps": [
                "Obtenha uma lista com mais de 200 registros (com ou sem filtro).",
                "Role a tela até o rodapé da tabela; o controle de página aparece apenas quando há mais de uma página.",
                "Clique em Anterior ou Próxima para mover uma página por vez.",
                "Para chegar a um registro específico, use busca ou filtro para reduzir a lista primeiro.",
            ],
            "note": (
                "O tamanho da página é fixo em 200 nesta versão. Não há seletor de "
                "tamanho de página nem preferência por usuário nessa feature."
            ),
        },
        {
            "heading": "Relatórios: inventário e trilha de movimentações",
            "body": (
                "Os relatórios de Inventário Patrimonial e de Trilha de Auditoria & "
                "Fluxo também são paginados com 200 registros por página e mostram "
                "o total real do filtro aplicado. Antes de exportar, você pode "
                "navegar pelo relatório pagina por pagina para conferir o conteúdo "
                "antes de baixar o arquivo."
            ),
        },
        {
            "heading": "Exportações íntegras (CSV, Excel, PDF)",
            "body": (
                "CSV, Excel e PDF do patrimônio e das movimentações são gerados com "
                "todos os registros do filtro aplicado — sem corte silencioso. Se por "
                "alguma razão técnica um limite residual aparecer, o sistema avisa "
                "antes na tela e o próprio arquivo traz o aviso (exibindo X de Y). "
                "Se o total for grande (acima de 10.000 registros) e você exportar "
                "PDF, a tela avisa previamente que a geração pode demorar."
            ),
            "note": (
                "As exportações de inventário e movimentações usam os mesmos filtros "
                "da tela de relatório e exportam o conjunto completo do filtro, não "
                "apenas a página que você está vendo. Para exportar, use os botões "
                "Baixar CSV / Exportar Excel / Exportar PDF na tela de relatório."
            ),
        },
        {
            "heading": "O que acontece se eu filtrar antes de exportar",
            "body": (
                "O arquivo baixado respeita exatamente os filtros que você aplicou "
                "(busca, status, categoria, local, responsável, período e demais). "
                "Os cabeçalhos, colunas, delimitador, encoding e nome do arquivo "
                "permancem os mesmos das versões anteriores."
            ),
        },
    ],
}
