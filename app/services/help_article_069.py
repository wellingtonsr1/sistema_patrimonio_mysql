"""Artigo da Central de Ajuda — Acessibilidade do login e inventário (feature 069).

Padrão help_article_068: conteúdo concentrado, importado por `help_service`
e integrado à Central de Ajuda (/ajuda).

Documenta para o usuário:
- navegação por teclado (skip-link, ordem natural, Enter submete);
- leitura de tela (rótulos em todos os campos, grupos com título,
  alertas de erro e contadores dinâmicos anunciados);
- foco visível nos cards de resultado da conferência;
- nada muda em rotas, permissões ou comportamento funcional.
"""
from typing import Dict

ARTIGO_ACESSIBILIDADE: Dict = {
    "id": "acessibilidade",
    "title": "Acessibilidade no login e inventário",
    "module": "Navegação & Relatórios",
    "icon": "bi-universal-access",
    "audience": "user",
    "summary": "Como o sistema funciona com teclado e leitor de tela no acesso e na conferência de inventário.",
    "keywords": [
        "acessibilidade", "teclado", "leitor de tela", "foco", "skip link",
        "pular para o conteúdo", "rótulo", "aria", " Enter", "senha",
        "conferência", "resultado", "pesquisa", "sob anúncio",
    ],
    "sections": [
        {
            "heading": "Navegar por teclado",
            "body": (
                "Todo o sistema pode ser operado sem mouse: a tecla Tab avança campo a campo\n"
                "na ordem da tela e o Enter submete os formulários. No login, ao abrir a\n"
                "página o cursor começa no campo de usuário. Nas telas autenticadas, a\n"
                "primeira tecla de Tab mostra um botão \"Pular para o conteúdo\", que leva\n"
                "direto ao corpo da página, atalhando o menu.\n\n"
                "Nos cards grandes de resultado da conferência (Encontrado, Local diferente,\n"
                "Não encontrado, Sem identificação) o card em foco recebe um contorno visible,\n"
                "complementando a marcação interna do próprio campo."
            ),
        },
        {
            "heading": "Com leitor de tela",
            "body": (
                "Todos os campos de formulário têm rótulo associado inclusive os compactos\n"
                "(buscas e filtros) — o leitor anuncia o nome do campo ao recebê-lo. O grupo\n"
                "\"Resultado da conferência\" é anunciado com título entre seus quatro opções;\n"
                "mensagens de erro em vermelho são anunciadas como alerta; na conferência\n"
                "offline, os contadores (conferidas, restantes, divergências, não previstos e\n"
                "pendências de sincronização) são anunciados automaticamente quando mudam.\n\n"
                "O botão de exibir a senha no login anuncia o estado atual (Mostrar/Ocultar)\n"
                "e alterna corretamente com Enter/Espaço."
            ),
        },
        {
            "heading": "Contraste e legibilidade",
            "body": (
                "O sistema mantém o contorno de foco padrão nos campos e botões (não há\n"
                "supressão de outline) e os temas claro e escuro usam tokens de cor com\n"
                "contraste mantido nos textos e estados. Confirmações destrutivas continuam\n"
                "sendo pedidas com caixa de diálogo do navegador, legível por leitores de tela."
            ),
        },
        {
            "heading": "O que não mudou",
            "body": (
                "Estes ajustes são de descrição e semântica das telas — nenhuma rota,\n"
                "permissão, validação, comportamento ou layout mudou. Filtragem, busca,\n"
                "autenticação e fluxo de conferência continuam idênticos."
            ),
        },
    ],
}
