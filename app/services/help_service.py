"""
Central de Ajuda / Manual do SisPatrimônio Pro.

Este módulo concentra TODO o conteúdo da documentação (artigos, categorias
e perguntas frequentes) em um único lugar, facilitando a manutenção: para
adicionar um novo artigo basta criar um item na lista ARTICLES e, se
desejado, referenciá-lo em uma categoria.

Regras de conteúdo:
- Documenta SOMENTE funcionalidades realmente existentes no sistema.
- Terminologia consistente com a interface (Equipamentos/Patrimônio,
  Fluxo & Movimentação, Manutenções, Colaboradores, Locais, Relatórios...).
- `audience`: "user" (qualquer usuário autenticado) ou "admin" (exige
  permissão administrativa para visualizar).

Seções de um artigo (campo `sections`):
- {"heading": ..., "body": ...}   → parágrafos (separados por linha em branco)
- {"heading": ..., "steps": [...]} → lista numerada (passo a passo)
- {"heading": ..., "note": ...}    → destaque/aviso

"""
from typing import Dict, List, Optional

# ============================================================================
# ARTIGOS
# ============================================================================

ARTICLES: List[Dict] = [
    # ------------------------------------------------------------------ #
    # PRIMEIROS PASSOS
    # ------------------------------------------------------------------ #
    {
        "id": "o-que-e-o-sistema",
        "title": "O que é o SisPatrimônio Pro",
        "module": "Primeiros Passos",
        "icon": "bi-box-seam",
        "audience": "user",
        "summary": "Visão geral do sistema de gestão patrimonial e dos módulos disponíveis.",
        "keywords": ["sistema", "visão geral", "módulos", "patrimônio", "introdução", "sobre"],
        "sections": [
            {
                "heading": "O que o sistema faz",
                "body": (
                    "O SisPatrimônio Pro é o sistema de gestão patrimonial do órgão. Ele controla o "
                    "cadastro de equipamentos (computadores, notebooks, monitores, impressoras, servidores "
                    "e demais bens), a movimentação entre setores e responsáveis, a impressão de "
                    "etiquetas patrimoniais, as manutenções e os relatórios do acervo.\n\n"
                    "Tudo o que acontece com um bem — entrada, entrega, transferência, manutenção, "
                    "devolução ou baixa — fica registrado no histórico (linha do tempo) do equipamento, "
                    "garantindo rastreabilidade total."
                ),
            },
            {
                "heading": "Módulos do sistema",
                "steps": [
                    "Dashboard — visão geral com indicadores do acervo.",
                    "Equipamentos — cadastro, consulta, detalhes, etiquetas e importação em massa.",
                    "Fluxo & Movimentação — transferências, entregas, devoluções e baixas.",
                    "Manutenções — ordens de serviço e reparos.",
                    "Colaboradores — cadastro dos responsáveis/custodiantes dos bens.",
                    "Locais — prédios, salas e departamentos.",
                    "Relatórios — inventário, trilha de auditoria e relação de colaboradores.",
                ],
            },
            {
                "heading": "Quem pode acessar o quê",
                "body": (
                    "O acesso é controlado por perfis. Cada perfil possui um conjunto de permissões, "
                    "por exemplo visualizar, cadastrar ou editar. Um usuário só enxerga os menus e "
                    "executa as ações para as quais possui permissão. Se você não vê um menu ou botão, "
                    "procure o administrador do sistema para verificar seu perfil de acesso."
                ),
            },
        ],
    },
    {
        "id": "entrar-e-sair",
        "title": "Como entrar e sair do sistema",
        "module": "Primeiros Passos",
        "icon": "bi-box-arrow-in-right",
        "audience": "user",
        "summary": "Login, logout, sessão e troca de senha.",
        "keywords": ["login", "logar", "entrar", "sair", "logout", "senha", "acesso"],
        "sections": [
            {
                "heading": "Entrar no sistema",
                "steps": [
                    "Acesse o endereço do sistema no navegador (ex.: http://localhost:8000).",
                    "Informe seu usuário (login) e sua senha.",
                    "Clique em Entrar.",
                ],
                "body": (
                    "Se você ainda não tem usuário, o administrador do sistema deve criá-lo e atribuir "
                    "seu perfil de acesso."
                ),
            },
            {
                "heading": "Sair do sistema",
                "body": (
                    "Clique no seu usuário (canto superior direito) e depois em Sair. A sessão é "
                    "encerrada no servidor e o acesso é revogado imediatamente."
                ),
            },
            {
                "heading": "Trocar minha senha",
                "steps": [
                    "Clique no seu usuário (canto superior direito).",
                    "Escolha Alterar senha.",
                    "Informe a senha atual e a nova senha (mínimo de 8 caracteres).",
                    "Confirme e clique em Alterar Senha.",
                ],
                "note": (
                    "Após a troca, você precisará fazer login novamente. Se esquecer a senha, o "
                    "administrador pode redefini-la."
                ),
            },
            {
                "heading": "Proteção contra tentativas de acesso",
                "body": (
                    "Após várias tentativas de login com senha incorreta, a conta é bloqueada "
                    "temporariamente. Aguarde alguns minutos ou procure o administrador."
                ),
            },
        ],
    },
    {
        "id": "conhecendo-a-interface",
        "title": "Conhecendo a interface",
        "module": "Primeiros Passos",
        "icon": "bi-layout-sidebar",
        "audience": "user",
        "summary": "Menu lateral, cabeçalho, dashboard e tema claro/escuro.",
        "keywords": ["interface", "menu", "navegação", "dashboard", "tema", "escuro", "claro"],
        "sections": [
            {
                "heading": "Como navegar",
                "body": (
                    "O menu no topo (e o menu lateral no celular) dá acesso aos módulos. Cada item do "
                    "menu aparece de acordo com o seu perfil de permissões — itens sem permissão não "
                    "são exibidos.\n\n"
                    "Na maioria das listas (equipamentos, movimentações) há uma caixa de pesquisa e "
                    "filtros para localizar rapidamente o que você procura."
                ),
            },
            {
                "heading": "Dashboard",
                "body": (
                    "O Dashboard é a primeira tela após o login. Ele mostra indicadores do acervo: "
                    "total de equipamentos, valor total, bens em uso, disponíveis em estoque, em "
                    "manutenção e as movimentações mais recentes."
                ),
            },
            {
                "heading": "Tema claro e escuro",
                "body": (
                    "Use o botão de lua/sol no canto superior direito para alternar entre os temas. "
                    "A preferência fica salva no seu navegador."
                ),
            },
        ],
    },

    # ------------------------------------------------------------------ #
    # PATRIMÔNIO / EQUIPAMENTOS
    # ------------------------------------------------------------------ #
    {
        "id": "cadastrar-equipamento",
        "title": "Como cadastrar um equipamento",
        "module": "Patrimônio & Equipamentos",
        "icon": "bi-laptop",
        "audience": "user",
        "summary": "Passo a passo para tombar um novo bem no patrimônio.",
        "keywords": ["cadastrar", "novo", "tombamento", "equipamento", "patrimônio", "bem", "tag"],
        "sections": [
            {
                "heading": "Antes de começar",
                "body": (
                    "Você precisa da permissão de cadastro de patrimônio. Tenha em mãos os dados do "
                    "bem: número de tombamento (tag), descrição, categoria, marca/modelo, número de "
                    "série e, se houver, nota fiscal e valor."
                ),
            },
            {
                "heading": "Passo a passo",
                "steps": [
                    "No menu, acesse Equipamentos.",
                    "Clique em Novo Equipamento.",
                    "Preencha o Nº de Tombamento (código único, ex.: PAT-00125).",
                    "Informe o nome/descrição e a categoria do bem.",
                    "Preencha marca, modelo, número de série e especificações.",
                    "Informe os dados fiscais (data de compra, valor, nota fiscal, fornecedor, garantia).",
                    "Defina a localização inicial e, se for o caso, o colaborador responsável (cautela).",
                    "Revise as informações e clique em Concluir Tombamento.",
                ],
            },
            {
                "heading": "O que acontece ao salvar",
                "body": (
                    "O bem é registrado com status Disponível (em estoque) ou Em uso (se informado um "
                    "responsável), e a entrada é gravada automaticamente no histórico do equipamento."
                ),
            },
        ],
    },
    {
        "id": "consultar-equipamentos",
        "title": "Como consultar e filtrar equipamentos",
        "module": "Patrimônio & Equipamentos",
        "icon": "bi-search",
        "audience": "user",
        "summary": "Busca por texto e filtros por status, categoria, local e responsável.",
        "keywords": ["consultar", "pesquisar", "buscar", "filtrar", "lista", "equipamentos", "status", "categoria"],
        "sections": [
            {
                "heading": "Como funciona",
                "body": (
                    "Na tela Equipamentos, digite na caixa de busca qualquer termo — tombamento, nome, "
                    "marca, modelo ou número de série — e pressione Filtrar.\n\n"
                    "Use os filtros ao lado para refinar por status (Disponível, Em uso, Em manutenção, "
                    "Baixado), categoria, local ou responsável."
                ),
            },
            {
                "heading": "Significado dos status",
                "steps": [
                    "Disponível — o bem está no estoque/almoxarifado, sem responsável.",
                    "Em Uso — o bem está alocado a um colaborador ou setor.",
                    "Em Manutenção — o bem está em reparo técnico.",
                    "Em Trânsito — o bem está em transporte/transferência.",
                    "Baixado — o bem foi descartado, leiloado ou perdido (baixa definitiva).",
                ],
            },
        ],
    },
    {
        "id": "detalhes-do-bem",
        "title": "Como visualizar os detalhes de um bem",
        "module": "Patrimônio & Equipamentos",
        "icon": "bi-eye",
        "audience": "user",
        "summary": "Ficha técnica, custódia, localização, depreciação, QR Code e linha do tempo.",
        "keywords": ["detalhes", "ficha", "histórico", "linha do tempo", "timeline", "depreciação", "qr", "código"],
        "sections": [
            {
                "heading": "Abrindo o detalhe",
                "body": (
                    "Clique sobre o tombamento ou o nome do equipamento na lista para abrir a página de "
                    "detalhes do bem."
                ),
            },
            {
                "heading": "O que a tela mostra",
                "steps": [
                    "Custódia e localização atual — quem é o responsável e onde o bem está.",
                    "Ficha técnica e dados fiscais — marca, modelo, série, nota fiscal, garantia.",
                    "Contabilidade e depreciação — valor de aquisição e valor contábil atual.",
                    "Etiqueta QR Code — código para identificação/impressão do bem.",
                    "Trilha de fluxo — todo o histórico de movimentações do bem, do mais recente ao mais antigo.",
                ],
            },
            {
                "heading": "Imprimir o termo",
                "body": (
                    "Quando uma movimentação gera termo (alocação ou devolução), o link Imprimir Termo "
                    "abre o documento pronto para impressão e assinatura."
                ),
            },
        ],
    },
    {
        "id": "etiquetas-patrimoniais",
        "title": "Como imprimir etiquetas patrimoniais (QR Code)",
        "module": "Patrimônio & Equipamentos",
        "icon": "bi-upc-scan",
        "audience": "user",
        "summary": "Selecionar bens e imprimir etiquetas em lote com QR Code e dados do patrimônio.",
        "keywords": ["etiqueta", "etiquetas", "imprimir", "qr", "código", "lote", "selecionar", "adesivo"],
        "sections": [
            {
                "heading": "Onde fica",
                "steps": [
                    "No menu, abra Equipamentos e clique em Etiquetas.",
                    "Use a busca e os filtros para localizar os bens desejados.",
                    "Marque os equipamentos (ou use Selecionar todos exibidos).",
                    "Clique em Imprimir etiquetas para gerar a folha.",
                ],
                "body": (
                    "A seleção fica guardada na própria página (mesmo que você filtre ou troque de "
                    "página), e o link pode ser compartilhado — quem abrir verá as mesmas etiquetas "
                    "selecionadas."
                ),
            },
            {
                "heading": "O que a etiqueta contém",
                "steps": [
                    "QR Code — leva à ficha do equipamento quando lido pela câmera do celular.",
                    "Nº de tombamento (patrimônio).",
                    "Descrição do bem.",
                    "Departamento e localização atuais.",
                ],
                "note": (
                    "Os dados vêm direto do cadastro. Se um bem não tiver localização, o campo "
                    "aparece vazio (—). A impressão usa folha A4 com 10 etiquetas por página; use a "
                    "prévia (Ctrl+P) para conferir antes de imprimir."
                ),
            },
            {
                "heading": "Segurança",
                "body": (
                    "Imprimir etiquetas não altera nenhum dado do patrimônio — é uma operação apenas "
                    "de consulta. Requer permissão de visualização de patrimônio."
                ),
            },
        ],
    },
    {
        "id": "importar-equipamentos",
        "title": "Como importar equipamentos em massa (CSV)",
        "module": "Patrimônio & Equipamentos",
        "icon": "bi-filetype-csv",
        "audience": "user",
        "summary": "Importação de vários bens de uma vez a partir de um arquivo CSV.",
        "keywords": ["importar", "csv", "planilha", "massa", "vários", "equipamentos"],
        "sections": [
            {
                "heading": "Passo a passo",
                "steps": [
                    "Na tela Equipamentos, clique em Importar CSV.",
                    "Selecione um arquivo .csv com os dados dos bens.",
                    "O sistema exibe uma pré-visualização antes de gravar.",
                    "Confirme a importação. Bens duplicados (mesmo tombamento) podem ser ignorados.",
                ],
            },
            {
                "heading": "Importante",
                "note": (
                    "A importação exige permissão de cadastro de patrimônio. A pré-visualização permite "
                    "conferir os dados antes de confirmar; erros de leitura do arquivo são exibidos "
                    "para correção."
                ),
            },
        ],
    },
    {
        "id": "corrigir-informacoes",
        "title": "Como corrigir informações cadastrais de um bem",
        "module": "Patrimônio & Equipamentos",
        "icon": "bi-pencil",
        "audience": "user",
        "summary": "Correção de dados de cadastro (técnica, fiscal e observações).",
        "keywords": ["corrigir", "editar", "alterar", "dados", "cadastro", "erro"],
        "sections": [
            {
                "heading": "Correção de dados cadastrais",
                "body": (
                    "A alteração de dados cadastrais (marca, modelo, nota fiscal, observações, estado "
                    "de conservação) é feita pela API do sistema, para usuários com permissão de edição "
                    "de patrimônio (ex.: perfil Gestor de TI ou Patrimônio).\n\n"
                    "Para correções em massa, utilize a reimportação CSV. Mudanças de responsável, "
                    "localização ou situação devem ser feitas por uma movimentação (ver Fluxo & "
                    "Movimentação), nunca por edição direta."
                ),
            },
            {
                "heading": "O que NÃO deve ser editado",
                "note": (
                    "Responsável, localização e status não se alteram por edição: eles mudam por "
                    "movimentação, para que tudo fique registrado no histórico do bem."
                ),
            },
        ],
    },

    # ------------------------------------------------------------------ #
    # FLUXO & MOVIMENTAÇÃO
    # ------------------------------------------------------------------ #
    {
        "id": "movimentar-equipamento",
        "title": "Como movimentar um equipamento",
        "module": "Fluxo & Movimentação",
        "icon": "bi-arrow-left-right",
        "audience": "user",
        "summary": "Entregar, transferir, devolver ou dar baixa em um bem, com registro no histórico.",
        "keywords": ["movimentar", "transferir", "alocar", "entregar", "devolver", "baixa", "responsável", "setor"],
        "sections": [
            {
                "heading": "Quando usar",
                "body": (
                    "Utilize uma movimentação sempre que um equipamento mudar de setor, localização ou "
                    "responsável, for enviado para manutenção, devolvido ao estoque ou der baixa. O "
                    "sistema registra tudo no histórico para manter a rastreabilidade do patrimônio."
                ),
            },
            {
                "heading": "Passo a passo",
                "steps": [
                    "Acesse Fluxo & Movimentação e clique em Nova Movimentação (ou, nos detalhes do bem, em Movimentar).",
                    "Selecione o equipamento.",
                    "Escolha o tipo de movimentação (ver artigo Tipos de movimentação).",
                    "Informe o destino: novo colaborador (cautela) e/ou novo local.",
                    "Descreva o motivo/justificativa.",
                    "Confirme e Grave.",
                ],
            },
            {
                "heading": "Termo de responsabilidade",
                "body": (
                    "Em alocações e devoluções, o sistema gera automaticamente um termo de "
                    "responsabilidade/cautela com os dados do bem e do colaborador, pronto para "
                    "impressão e assinatura."
                ),
            },
        ],
    },
    {
        "id": "tipos-de-movimentacao",
        "title": "Entendendo os tipos de movimentação",
        "module": "Fluxo & Movimentação",
        "icon": "bi-diagram-3",
        "audience": "user",
        "summary": "Explicação amigável de cada tipo de movimentação disponível.",
        "keywords": ["tipos", "alocação", "cautela", "transferência", "devolução", "baixa", "descarte", "manutenção"],
        "sections": [
            {
                "heading": "Tipos disponíveis",
                "steps": [
                    "Alocação a Colaborador — entrega do equipamento a um funcionário (cautela).",
                    "Transferência de Setor/Filial — mudança de sala, prédio, filial ou departamento.",
                    "Devolução ao Estoque — recolhimento do bem (ex.: desligamento ou troca).",
                    "Baixa / Descarte Definitivo — obsolescência, perda, quebra ou leilão.",
                    "Envio/Retorno de Manutenção — saída e reintegração do bem após reparo.",
                    "Atualização de Estado — vistoria que altera a condição de conservação.",
                ],
            },
            {
                "heading": "Qual tipo escolher",
                "body": (
                    "Regra prática: mudou o responsável? Alocação. Mudou o local/setor? Transferência. "
                    "O bem voltou para o almoxarifado? Devolução ao estoque. O bem não será mais usado? "
                    "Baixa/descarte."
                ),
            },
        ],
    },
    {
        "id": "historico-do-bem",
        "title": "Como consultar o histórico de um bem",
        "module": "Fluxo & Movimentação",
        "icon": "bi-clock-history",
        "audience": "user",
        "summary": "Linha do tempo do bem e relatório de trilha de auditoria.",
        "keywords": ["histórico", "linha do tempo", "timeline", "trilha", "auditoria", "movimentações"],
        "sections": [
            {
                "heading": "Histórico individual",
                "body": (
                    "Abra os detalhes do bem e role até a Trilha de Fluxo & Movimentações. Cada evento "
                    "mostra data/hora, tipo, origem, destino, motivo e quem registrou."
                ),
            },
            {
                "heading": "Histórico geral",
                "body": (
                    "O relatório Trilha de Auditoria (menu Relatórios) consolida todas as movimentações "
                    "do sistema, com filtros por tipo, período, local e colaborador, e pode ser "
                    "exportado em CSV."
                ),
            },
        ],
    },

    # ------------------------------------------------------------------ #
    # MANUTENÇÕES
    # ------------------------------------------------------------------ #
    {
        "id": "abrir-ordem-servico",
        "title": "Como abrir uma ordem de serviço (manutenção)",
        "module": "Manutenções",
        "icon": "bi-wrench",
        "audience": "user",
        "summary": "Registrar o envio de um equipamento para reparo.",
        "keywords": ["manutenção", "ordem de serviço", "os", "reparo", "defeito", "preventiva", "corretiva"],
        "sections": [
            {
                "heading": "Passo a passo",
                "steps": [
                    "Acesse Manutenções e clique em Abrir Nova OS.",
                    "Selecione o equipamento.",
                    "Escolha o tipo: Preventiva, Corretiva ou Upgrade.",
                    "Informe a assistência/técnico responsável.",
                    "Descreva o defeito ou escopo do serviço.",
                    "Informe o custo estimado (se houver).",
                    "Clique em Abrir OS.",
                ],
            },
            {
                "heading": "O que acontece",
                "body": (
                    "O equipamento passa automaticamente para o status EM MANUTENÇÃO e a saída é "
                    "registrada no histórico do bem."
                ),
            },
        ],
    },
    {
        "id": "finalizar-manutencao",
        "title": "Como finalizar uma manutenção",
        "module": "Manutenções",
        "icon": "bi-check2-circle",
        "audience": "user",
        "summary": "Registrar a solução aplicada e concluir a ordem de serviço.",
        "keywords": ["finalizar", "concluir", "solução", "peças", "custo", "manutenção"],
        "sections": [
            {
                "heading": "Passo a passo",
                "steps": [
                    "Na lista de Manutenções, localize a OS em andamento.",
                    "Clique em Finalizar Manutenção.",
                    "Descreva a solução aplicada e os custos finais.",
                    "Confirme a finalização.",
                ],
            },
            {
                "heading": "O que acontece",
                "body": (
                    "A OS é marcada como concluída, o status do equipamento retorna para Disponível e o "
                    "retorno da manutenção é registrado no histórico do bem."
                ),
            },
        ],
    },

    # ------------------------------------------------------------------ #
    # INVENTÁRIOS
    # ------------------------------------------------------------------ #
    {
        "id": "inventarios-overview",
        "title": "Inventário patrimonial (visão geral)",
        "module": "Inventários",
        "icon": "bi-clipboard-check",
        "audience": "user",
        "summary": "O que é o inventário, ciclo de vida, resultados possíveis e o que ele nunca altera.",
        "keywords": ["inventário", "inventários", "conferência", "conferir", "acervo", "ata", "ciclo de vida"],
        "sections": [
            {
                "heading": "O que é",
                "body": (
                    "O inventário é a conferência física do acervo. No menu Inventários você cria um "
                    "inventário com nome, escopo opcional por local e/ou setor/departamento (vazio = "
                    "todo o acervo) e observações. Ao criar, o sistema gera a lista de bens esperados "
                    "(foto do cadastro naquele momento, imune a edições posteriores)."
                ),
            },
            {
                "heading": "Localizar inventários",
                "body": (
                    "Na listagem de Inventários há busca por código ou nome do inventário e filtro por "
                    "status (PLANEJADO, EM_ANDAMENTO, ENCERRADO) — use Filtrar para aplicar e Limpar "
                    "para voltar à lista completa."
                ),
            },
            {
                "heading": "Ciclo de vida",
                "steps": [
                    "PLANEJADO — criado, lista de bens esperados gerada; conferências ainda não são aceitas.",
                    "EM_ANDAMENTO — conferência liberada após Iniciar Inventário; itens podem ser conferidos e re-conferidos.",
                    "ENCERRADO — Encerrar Inventário exige todos os bens esperados conferidos; os itens ficam travados.",
                ],
            },
            {
                "heading": "Resultados possíveis de um item",
                "steps": [
                    "PENDENTE — ainda sem conferência.",
                    "ENCONTRADO — bem conferido no local previsto.",
                    "LOCAL_DIFERENTE — bem encontrado em outro local (registra-se onde foi encontrado).",
                    "NAO_ENCONTRADO — bem não localizado na conferência.",
                    "SEM_IDENTIFICACAO — item sem identificação legível (ex.: sem etiqueta/tombamento).",
                ],
            },
            {
                "heading": "O que o inventário NÃO faz",
                "note": (
                    "O inventário nunca altera o cadastro: bens, movimentações e locais não são "
                    "modificados pela conferência. Divergências (local diferente, não encontrado) ficam "
                    "apenas registradas para tratamento pelos fluxos próprios (movimentações, manutenção)."
                ),
            },
            {
                "heading": "Permissões",
                "note": (
                    "Visualizar, criar, conferir e encerrar inventários são permissões separadas "
                    "(inventario.visualizar, inventario.criar, inventario.conferir, inventario.encerrar). "
                    "Se um botão não aparece, seu perfil não possui a permissão correspondente."
                ),
            },
        ],
    },
    {
        "id": "conferir-inventario",
        "title": "Como conferir bens em um inventário",
        "module": "Inventários",
        "icon": "bi-ui-checks",
        "audience": "user",
        "summary": "Conferência em campo por bem, re-conferência com confirmação, bens não previstos e ata.",
        "keywords": ["conferir", "conferência", "re-conferência", "não previsto", "ata", "qrcode", "qr", "buscar"],
        "sections": [
            {
                "heading": "Iniciar a conferência",
                "steps": [
                    "No inventário (status PLANEJADO), clique em Iniciar Inventário — isso libera as conferências.",
                    "Na página do inventário, use o campo Buscar para localizar um bem da lista.",
                ],
            },
            {
                "heading": "Conferir um bem",
                "steps": [
                    "Abra a conferência pelo item (ou pela ficha do bem, via QR Code/busca).",
                    "Escolha o Resultado da conferência: Encontrado, Local diferente, Não encontrado ou Sem identificação.",
                    "Se for local diferente, informe o Local onde foi encontrado.",
                    "Escreva uma Observação, se necessário (opcional).",
                    "Clique em Registrar conferência.",
                ],
            },
            {
                "heading": "Re-conferência de item já conferido",
                "body": (
                    "Enquanto o inventário estiver EM_ANDAMENTO, um item já conferido pode ser conferido "
                    "novamente: a página mostra quem conferiu antes, quando e o resultado anterior, e pede "
                    "confirmação antes de substituir o registro. Itens PENDENTE registram diretamente; após "
                    "o encerramento, nenhum item aceita nova conferência."
                ),
            },
            {
                "heading": "Bem não previsto na lista",
                "steps": [
                    "Na página do inventário, use Registrar como não previsto.",
                    "Informe a identificação do bem encontrado em campo (ex.: tombamento lido na etiqueta).",
                    "O item entra na lista como não previsto, com o resultado registrado.",
                ],
            },
            {
                "heading": "Encerrar e ata",
                "body": (
                    "Encerrar Inventário exige que todos os bens esperados estejam conferidos; depois disso "
                    "os itens ficam travados. A ata comprobatória do inventário pode ser exportada (CSV, "
                    "Excel e PDF) pela página do inventário."
                ),
            },
        ],
    },

    # ------------------------------------------------------------------ #
    # COLABORADORES & LOCAIS
    # ------------------------------------------------------------------ #
    {
        "id": "cadastrar-colaboradores",
        "title": "Como cadastrar colaboradores (custodiantes)",
        "module": "Colaboradores & Locais",
        "icon": "bi-people",
        "audience": "user",
        "summary": "Cadastro de colaboradores, importação em massa e consulta de bens sob custódia.",
        "keywords": ["colaborador", "funcionário", "custodiante", "responsável", "matrícula", "cadastrar", "provisória", "PROV", "departamento", "setor"],
        "sections": [
            {
                "heading": "Passo a passo",
                "steps": [
                    "Acesse Colaboradores e clique em Cadastrar Colaborador.",
                    "Informe nome, e-mail e CPF. A matrícula é opcional (veja abaixo).",
                    "Informe o cargo e selecione o departamento/setor no campo de seleção (lista oficial, derivada dos locais cadastrados).",
                    "Clique em Salvar.",
                ],
            },
            {
                "heading": "Colaborador sem matrícula: identificador provisório",
                "body": (
                    "Se a matrícula funcional ainda não estiver disponível, deixe o campo em branco: "
                    "o sistema gera automaticamente um identificador provisório no formato PROV-000001 "
                    "(sequencial, exclusivo do sistema — não pode ser digitado pelo usuário). Na listagem, "
                    "nos detalhes e nos termos de responsabilidade, o número aparece com a marcação \"provisória\". "
                    "O colaborador provisório participa normalmente de todas as operações patrimoniais: "
                    "alocação/cautela, transferência, devolução, inventário e emissão de termos."
                ),
            },
            {
                "heading": "Informar a matrícula oficial depois",
                "body": (
                    "Quando a matrícula funcional for conhecida, abra a edição do colaborador: se a "
                    "identificação atual for provisória, o campo de matrícula fica editável — informe a "
                    "matrícula oficial e salve. O colaborador permanece o mesmo (os bens, movimentações, "
                    "termos e o histórico ficam vinculados a ele, sem quebrar nada); os registros antigos "
                    "mantêm a identificação da época, e as emissões futuras já exibem a matrícula oficial. "
                    "Colaboradores que já possuem matrícula oficial continuam com ela inalterável pela interface."
                ),
            },
            {
                "heading": "Departamento/Setor: campo de seleção da lista oficial",
                "body": (
                    "O campo \"Departamento / Setor\" não aceita mais texto livre: é um dropdown que apresenta "
                    "a lista oficial de setores, derivada dos departamentos dos locais cadastrados. Novos valores "
                    "oficiais surgem ao cadastrar ou editar locais; não é possível criar um setor digitando um "
                    "nome novo no campo. A obrigatoriedade do campo é validada no servidor ao salvar. Na edição, "
                    "o setor atual já vem selecionado, e salvar sem alterá-lo é sempre permitido."
                ),
            },
            {
                "heading": "Pesquisar colaboradores",
                "body": (
                    "Na listagem de colaboradores, use o campo de pesquisa acima da tabela para "
                    "localizar rapidamente: digite parte da matrícula, nome, cargo, departamento "
                    "ou e-mail — não é preciso escolher o campo. A pesquisa ignora maiúsculas e "
                    "minúsculas e aceita correspondência parcial; para voltar à lista completa, "
                    "limpe o campo e pesquise novamente ou use o botão Limpar."
                ),
            },
            {
                "heading": "Importação em massa",
                "body": (
                    "Também é possível importar colaboradores via arquivo CSV, com pré-visualização "
                    "antes de confirmar (exige permissão de cadastro de colaboradores)."
                ),
            },
            {
                "heading": "Bens sob custódia",
                "body": (
                    "Na página de detalhes do colaborador, a seção Equipamentos sob Custódia lista "
                    "todos os bens atualmente alocados àquela pessoa."
                ),
            },
        ],
    },
    {
        "id": "cadastrar-locais",
        "title": "Como cadastrar locais e departamentos",
        "module": "Colaboradores & Locais",
        "icon": "bi-geo-alt",
        "audience": "user",
        "summary": "Cadastro de unidades, prédios, andares, salas e departamentos.",
        "keywords": ["local", "departamento", "setor", "prédio", "andar", "sala", "filial"],
        "sections": [
            {
                "heading": "Passo a passo",
                "steps": [
                    "Acesse Locais e clique em Cadastrar Novo Local.",
                    "Informe o nome do local, a filial e o departamento.",
                    "Preencha prédio, andar e sala quando aplicável.",
                    "Informe o gestor responsável e uma descrição, se desejar.",
                    "Clique em Salvar.",
                ],
            },
            {
                "heading": "Ver bens por local",
                "body": (
                    "Na lista de locais, o botão Ver Bens abre a listagem de equipamentos filtrada "
                    "pelaquele local."
                ),
            },
            {
                "heading": "Pesquisar locais",
                "body": (
                    "Use o campo de pesquisa acima da tabela para localizar um local pelo "
                    "Nome / Identificação (a primeira coluna). A pesquisa aceita trechos do nome, "
                    "ignora maiúsculas e minúsculas e ignora espaços extras no início e no fim do termo. "
                    "Ela não busca por filial, departamento ou gestor — apenas pelo nome exibido no registro. "
                    "Use Filtrar para aplicar e Limpar para voltar à lista completa."
                ),
            },
            {
                "heading": "Exportar locais",
                "body": (
                    "O botão Exportar CSV, no cabeçalho da tela, baixa o arquivo locais.csv com "
                    "todos os locais cadastrados, na mesma ordenação da listagem (filial, "
                    "departamento, nome). O arquivo contém apenas os dados cadastrais da tabela "
                    "(nome, filial, departamento, prédio, andar, sala e gestor), sem as colunas de "
                    "interface (Ações e a contagem de bens), no formato CSV padrão do sistema "
                    "(separador ;, codificação UTF-8 com BOM — abre direto no Excel). A exportação "
                    "não é afetada por filtros de pesquisa ativos na tela. É necessário ter a "
                    "permissão de exportação de relatórios (o botão só aparece para quem pode "
                    "exportar)."
                ),
            },
        ],
    },

    # ------------------------------------------------------------------ #
    # RELATÓRIOS & EXPORTAÇÕES
    # ------------------------------------------------------------------ #
    {
        "id": "relatorios",
        "title": "Relatórios disponíveis",
        "module": "Relatórios & Exportações",
        "icon": "bi-file-earmark-text",
        "audience": "user",
        "summary": "Relatório Contábil-Físico, trilha de auditoria e relação de colaboradores.",
        "keywords": ["relatórios", "inventário", "trilha", "auditoria", "colaboradores", "imprimir"],
        "sections": [
            {
                "heading": "Quais relatórios existem",
                "steps": [
                    "Relatório Contábil-Físico — listagem analítica de todos os bens com depreciação e valor contábil.",
                    "Trilha de Auditoria — todas as movimentações do acervo, com origem, destino e operador.",
                    "Relação de Colaboradores — colaboradores e a quantidade de bens sob custódia de cada um.",
                ],
            },
            {
                "heading": "Como gerar",
                "body": (
                    "Acesse o menu Relatórios e escolha o relatório desejado. Todos podem ser impressos "
                    "pelo botão Imprimir do navegador."
                ),
            },
            {
                "heading": "Acesso",
                "note": (
                    "A visualização de relatórios exige permissão relatorios.visualizar; a exportação "
                    "em CSV exige permissão adicional de exportação."
                ),
            },
        ],
    },
    {
        "id": "exportar-csv",
        "title": "Como exportar os dados em CSV",
        "module": "Relatórios & Exportações",
        "icon": "bi-download",
        "audience": "user",
        "summary": "Baixar inventário, movimentações, colaboradores e locais em arquivo CSV.",
        "keywords": ["exportar", "csv", "baixar", "download", "planilha", "dados", "locais", "excel"],
        "sections": [
            {
                "heading": "Onde exportar",
                "body": (
                    "Os relatórios Relatório Contábil-Físico, Trilha de Auditoria e Relação de Colaboradores "
                    "possuem o botão Baixar CSV.\n\n"
                    "Além dos relatórios, as telas Colaboradores, Dashboard (Relatório Contábil-Físico), "
                    "Movimentações e Locais possuem o botão Exportar CSV, que baixa o arquivo direto do "
                    "cabeçalho da tela — incluindo a exportação de todos os locais (arquivo locais.csv, "
                    "com os dados cadastrais da tabela, sem as colunas de interface). Os arquivos são "
                    "compatíveis com planilhas eletrônicas (separador ; e codificação UTF-8 com BOM, "
                    "abrindo direto no Excel)."
                ),
            },
            {
                "heading": "Permissão",
                "note": (
                    "A exportação exige permissão específica (relatorios.exportar). Se o botão não "
                    "aparecer, seu perfil não possui essa permissão."
                ),
            },
        ],
    },

    # ------------------------------------------------------------------ #
    # ADMINISTRAÇÃO
    # ------------------------------------------------------------------ #
    {
        "id": "gerenciar-usuarios",
        "title": "Como criar e gerenciar usuários (administração)",
        "module": "Administração",
        "icon": "bi-person-gear",
        "audience": "admin",
        "summary": "Criar usuários, atribuir perfis, bloquear e redefinir senhas.",
        "keywords": ["usuários", "criar", "perfis", "bloquear", "desbloquear", "senha", "admin"],
        "sections": [
            {
                "heading": "Acessando a administração",
                "body": (
                    "No menu Administração, a tela Usuários lista todos os usuários com busca, status, "
                    "perfis e último acesso."
                ),
            },
            {
                "heading": "Criar um usuário",
                "steps": [
                    "Clique em Novo Usuário.",
                    "Informe usuário (login), senha (mínimo 8 caracteres), nome e e-mail.",
                    "Marque os perfis de acesso — comece com o mínimo necessário (menor privilégio).",
                    "Clique em Criar Usuário.",
                ],
            },
            {
                "heading": "Editar, bloquear e redefinir senha",
                "steps": [
                    "Editar — altera nome, e-mail, situação da conta e os perfis atribuídos.",
                    "Bloquear/Desbloquear — o acesso é revogado imediatamente; sessões ativas são invalidadas.",
                    "Redefinir Senha — define nova senha e exige novo login do usuário.",
                ],
            },
            {
                "heading": "Redefinir senha pela linha de comando (servidor)",
                "steps": [
                    "No servidor, execute: python -m app.cli reset-password --username usuario",
                    "Digite a nova senha e a confirmação — a digitação é oculta e a senha nunca é informada como argumento do comando.",
                    "As sessões ativas do usuário são invalidadas; perfis e a situação da conta permanecem inalterados.",
                    "Usuários do Active Directory não são afetados: a senha deles é mantida no próprio AD.",
                ],
            },
            {
                "heading": "Regras de segurança",
                "note": (
                    "Um usuário não pode bloquear a si mesmo, e o sistema não permite remover ou "
                    "desativar o último administrador ativo — isso evita deixar o sistema sem "
                    "administração."
                ),
            },
        ],
    },
    {
        "id": "perfis-e-permissoes",
        "title": "Como criar e editar perfis e permissões (administração)",
        "module": "Administração",
        "icon": "bi-shield-lock",
        "audience": "admin",
        "summary": "Entender e ajustar os perfis de acesso e suas permissões granulares.",
        "keywords": ["perfis", "permissões", "papéis", "acesso", "rbac", "admin"],
        "sections": [
            {
                "heading": "O que são perfis",
                "body": (
                    "Um perfil agrupa permissões. Os perfis padrão do sistema são Administrador, "
                    "Gestor de TI, Técnico de TI, Patrimônio, Almoxarifado, Auditor e Consulta. Perfis "
                    "padrão podem ser editados, mas não excluídos."
                ),
            },
            {
                "heading": "Criar ou editar um perfil",
                "steps": [
                    "Acesse Administração → Perfis & Permissões.",
                    "Clique em Novo Perfil (ou Editar em um perfil existente).",
                    "Informe o nome e a descrição.",
                    "Marque as permissões desejadas, agrupadas por módulo.",
                    "Clique em Salvar Perfil.",
                ],
            },
            {
                "heading": "Como as permissões funcionam",
                "body": (
                    "Cada permissão segue o padrão módulo.ação, como patrimonio.visualizar ou "
                    "patrimonio.criar. O usuário só executa uma ação se possuir a permissão "
                    "correspondente — por isso, atribua sempre o menor conjunto de permissões "
                    "necessário para a função."
                ),
            },
        ],
    },
    {
        "id": "integracao-active-directory",
        "title": "Integração com Active Directory (administração)",
        "module": "Administração",
        "icon": "bi-hdd-network",
        "audience": "admin",
        "summary": "Ativar login via AD/LDAP, mapear grupos a perfis e entender provisionamento e erros comuns.",
        "keywords": ["active directory", "ad", "ldap", "ldaps", "samba", "domínio", "grupo", "mapeamento", "integração", "admin"],
        "sections": [
            {
                "heading": "O que a integração faz",
                "body": (
                    "Permite que usuários do domínio (Microsoft AD ou Samba AD DC) entrem no sistema com a "
                    "própria conta, via LDAP/LDAPS. O AD apenas autentica: as permissões continuam 100% "
                    "internas (perfis e permissões do SisPatrimônio) — nenhum acesso é concedido pelo AD. "
                    "Contas locais existentes continuam funcionando normalmente."
                ),
            },
            {
                "heading": "Como ativar",
                "steps": [
                    "Acesse Administração → Integração AD.",
                    "Marque Habilitar integração com Active Directory.",
                    "Informe o Servidor AD e a Porta (389 para LDAP; 636 para LDAPS).",
                    "Recomendado: marque Usar LDAPS (recomendado, porta 636) e Validar certificado TLS.",
                    "Informe a Base DN (ex.: DC=empresa,DC=local) e, se desejar restringir a busca, o DN de busca de usuários.",
                    "Clique em Testar Conexão e, estando ok, em Salvar Configuração.",
                ],
                "note": (
                    "As variáveis de ambiente AD_* (AD_SERVER, AD_BASE_DN, AD_BIND_USER, AD_BIND_PASSWORD etc.) "
                    "servem de valores iniciais/fallback dos campos da tela — a senha de serviço existe somente "
                    "no ambiente, nunca no banco."
                ),
            },
            {
                "heading": "Mapear grupos do AD a perfis",
                "steps": [
                    "Na mesma tela, informe o Grupo AD (o CN do grupo, ex.: GRP-SISPAT-TECNICOS-TI) e o Perfil existente.",
                    "Defina a Prioridade (quando um usuário pertence a vários grupos mapeados, vence o menor número).",
                    "Clique em Adicionar Mapeamento — repita para cada grupo autorizado.",
                    "Opcionalmente, use Prioridade dos grupos (opcional) para sobrepor a prioridade pela ordem dos grupos.",
                    "Para revogar um grupo, use Remover mapeamento — sem grupo mapeado, o login do AD é negado.",
                ],
                "note": (
                    "Somente entra no sistema quem pertencer a um grupo explicitamente mapeado. Usuários do "
                    "domínio sem grupo mapeado não recebem usuário, colaborador, perfil ou permissão — apenas "
                    "a tentativa fica registrada na auditoria. Perfis atribuídos manualmente nunca são removidos "
                    "pela sincronização do AD."
                ),
            },
            {
                "heading": "Primeiro login de um usuário do AD",
                "body": (
                    "Confirmado o grupo mapeado, o usuário do sistema é criado automaticamente e vinculado ao "
                    "colaborador existente por e-mail/matrícula (nunca duplica cadastro) — a tela oferece as "
                    "opções Criar usuário do sistema automaticamente quando autenticar no AD e Vincular "
                    "colaborador existente pelo e-mail (nunca duplica cadastro). Dados patrimoniais do "
                    "colaborador (matrícula, CPF, cargo, setor) não são sobrescritos pelo AD. A senha do "
                    "usuário do AD nunca é armazenada no SisPatrimônio."
                ),
            },
            {
                "heading": "Mensagens e erros comuns",
                "steps": [
                    "\"autenticado, mas não possui um perfil autorizado\" — o usuário autentica no AD, mas não está em nenhum grupo mapeado.",
                    "Credencial inválida — usuário ou senha incorretos no diretório.",
                    "Conta desabilitada — o usuário está desabilitado no próprio AD (userAccountControl).",
                    "AD indisponível — o controlador de domínio não respondeu (verifique servidor, porta e rede).",
                    "Login falha como credencial inválida mesmo com senha correta — confira o DN de busca de usuários: vazio, a busca usa a Base DN inteira; um DN apontando para uma OU sem os usuários faz a busca não encontrá-los (o log registra a base usada).",
                ],
            },
            {
                "heading": "Segurança",
                "note": (
                    "A senha do usuário nunca é persistida, logada ou auditada. LDAPS com validação de "
                    "certificado é o recomendado em produção; desativar a validação TLS é uma escolha explícita "
                    "do administrador (ambientes sem CA publicada). A integração adiciona eventos próprios na "
                    "trilha de auditoria — sempre sem credenciais."
                ),
            },
        ],
    },
    {
        "id": "auditoria",
        "title": "Como consultar a trilha de auditoria (administração)",
        "module": "Administração",
        "icon": "bi-journal-check",
        "audience": "admin",
        "summary": "Consultar o registro de logins, ações e acessos negados do sistema.",
        "keywords": ["auditoria", "trilha", "log", "registro", "ip", "ações", "admin"],
        "sections": [
            {
                "heading": "O que a auditoria registra",
                "body": (
                    "O sistema registra automaticamente logins, falhas de login, logout, criações e "
                    "alterações, bloqueios, redefinições de senha, mudanças de perfis, movimentações "
                    "patrimoniais e tentativas de acesso sem permissão."
                ),
            },
            {
                "heading": "Como consultar",
                "steps": [
                    "Acesse Administração → Auditoria.",
                    "Use os filtros por módulo, ação, resultado ou texto de busca.",
                    "Nos registros com alteração de dados, abra Detalhes para ver os dados anteriores e posteriores.",
                ],
            },
            {
                "heading": "Importante",
                "note": (
                    "A trilha de auditoria é somente leitura: não há como editar ou apagar registros "
                    "pela interface. A consulta exige permissão auditoria.visualizar."
                ),
            },
        ],
    },
    {
        "id": "backups",
        "title": "Como gerar e baixar backups (administração)",
        "module": "Administração",
        "icon": "bi-archive",
        "audience": "admin",
        "summary": "Gerar um backup manual do banco de dados, consultar os backups disponíveis e baixá-los.",
        "keywords": ["backup", "cópia", "segurança", "dump", "restauração", "admin"],
        "sections": [
            {
                "heading": "O que o backup contém",
                "body": (
                    "O backup é um dump SQL consistente do banco de dados do sistema, gerado pelo "
                    "utilitário nativo do MariaDB/MySQL e comprimido em gzip (.sql.gz). Ele contém "
                    "todos os dados persistidos do sistema (patrimônio, colaboradores, usuários, "
                    "perfis, movimentações, manutenção, inventário e auditoria). O arquivo é "
                    "armazenado no servidor, no diretório data/backups/, identificado por data/hora "
                    "em UTC (backup_AAAAMMDD_HHMMSS_micros.sql.gz)."
                ),
            },
            {
                "heading": "Como gerar e baixar",
                "steps": [
                    "Acesse Administração → Backups.",
                    "Clique em Gerar backup e aguarde a confirmação (pode levar alguns instantes).",
                    "A listagem mostra os backups disponíveis, do mais recente para o mais antigo, com data/hora, tamanho, Integridade e SHA-256.",
                    "Use Baixar para salvar o arquivo em seu computador; o SHA-256 exibido deve bater com o sha256sum do arquivo baixado.",
                ],
            },
            {
                "heading": "Importante",
                "note": (
                    "O backup é manual (sem agendamento e sem exclusão automática) e cobre o banco de dados. "
                    "A geração é atômica: só aparecem na lista arquivos completos e verificados. Toda operação é "
                    "registrada na trilha de auditoria. A restauração não é executada pelo sistema: "
                    "continua sendo política operacional do servidor. A função exige a permissão "
                    "backup.gerenciar."
                ),
            },
        ],
    },
]

# ============================================================================
# PERGUNTAS FREQUENTES (FAQ)
# ============================================================================

FAQ: List[Dict] = [
    {
        "question": "A integração com Active Directory/LDAP está disponível?",
        "answer": (
            "Sim. A autenticação pode ser integrada ao Active Directory (LDAP/LDAPS) pelo "
            "administrador, na tela Administração → Integração AD: informa-se o servidor, o Base DN "
            "e quais grupos do AD correspondem a cada perfil do sistema. Só entra no sistema o "
            "usuário cujo grupo estiver mapeado para um perfil; contas locais continuam funcionando "
            "normalmente. Sem a integração configurada, o acesso é feito com usuário e senha "
            "cadastrados no próprio sistema. Veja o artigo Integração com Active Directory "
            "(administração) para o passo a passo completo."
        ),
    },
    {
        "question": "Como localizar um equipamento?",
        "answer": (
            "Acesse Equipamentos e use a caixa de busca (tombamento, nome, marca, modelo ou número de "
            "série) ou os filtros de status, categoria, local e responsável. Nos detalhes do bem você "
            "vê a localização e o responsável atuais."
        ),
    },
    {
        "question": "Como alterar o responsável de um equipamento?",
        "answer": (
            "Use uma movimentação: abra o bem e clique em Movimentar, escolha Alocação a Colaborador "
            "(ou Transferência de Setor/Filial), informe o novo responsável e o motivo. O histórico "
            "registra a mudança automaticamente."
        ),
    },
    {
        "question": "Como consultar o histórico de um bem?",
        "answer": (
            "Abra os detalhes do equipamento e veja a Trilha de Fluxo & Movimentações. Para uma visão "
            "geral de tudo, use o relatório Trilha de Auditoria no menu Relatórios."
        ),
    },
    {
        "question": "Como registrar uma manutenção?",
        "answer": (
            "Acesse Manutenções e clique em Abrir Nova OS. Selecione o equipamento, o tipo de "
            "manutenção, descreva o defeito e salve. O bem passa automaticamente para EM MANUTENÇÃO. "
            "Ao finalizar o reparo, use Concluir na lista de manutenções."
        ),
    },
    {
        "question": "Como gerar um relatório?",
        "answer": (
            "No menu Relatórios escolha Relatório Contábil-Físico, Trilha de Auditoria ou Relação de "
            "Colaboradores. Todos podem ser impressos pelo botão Imprimir."
        ),
    },
    {
        "question": "Como exportar os dados?",
        "answer": (
            "Os relatórios possuem o botão Baixar CSV, que gera um arquivo compatível com planilhas. "
            "As telas Colaboradores, Dashboard, Movimentações e Locais também têm o botão Exportar CSV, "
            "que baixa o arquivo direto. A exportação exige permissão específica no seu perfil."
        ),
    },
    {
        "question": "O que fazer quando um equipamento não é encontrado na busca?",
        "answer": (
            "Confira a grafia do tombamento e limpe os filtros aplicados. Verifique se o bem não está "
            "com status Baixado (filtro Status). Se ainda assim não aparecer, o seu perfil pode não "
            "ter acesso de visualização ao módulo — procure o administrador."
        ),
    },
    {
        "question": "Como corrigir uma informação cadastrada incorretamente?",
        "answer": (
            "Correções de dados cadastrais são feitas pela API do sistema (para perfis com permissão "
            "de edição) ou pela reimportação CSV. Responsável, localização e status não devem ser "
            "editados diretamente: use uma movimentação para manter o histórico correto."
        ),
    },
    {
        "question": "Esqueci minha senha. O que faço?",
        "answer": (
            "Procure o administrador do sistema, que pode redefinir sua senha pela tela "
            "Administração → Usuários. Você poderá trocá-la depois em Alterar senha, no menu do seu "
            "usuário."
        ),
    },
    {
        "question": "Por que não vejo alguns menus ou botões?",
        "answer": (
            "O menu e os botões são exibidos conforme o seu perfil de permissões. Se uma ação não "
            "aparece, seu perfil não possui a permissão correspondente. Solicite a atribuição do "
            "perfil adequado ao administrador."
        ),
    },
    {
        "question": "Como o inventário é concluído?",
        "answer": (
            "Após conferir todos os bens esperados, use Encerrar Inventário: os itens ficam travados e "
            "a ata comprobatória pode ser exportada em CSV, Excel e PDF. Divergências (local diferente ou "
            "bem não encontrado) devem ser tratadas depois pelos fluxos de movimentação e manutenção — "
            "o inventário não altera o cadastro."
        ),
    },
    {
        "question": "Como devolver um equipamento ao estoque?",
        "answer": (
            "Abra o bem e clique em Movimentar, escolha Devolução ao Estoque e informe o motivo. O "
            "status volta para Disponível e o termo de devolução é gerado."
        ),
    },
]

# ============================================================================
# CATEGORIAS (cards da página central)
# ============================================================================

CATEGORIES: List[Dict] = [
    {
        "key": "primeiros-passos",
        "title": "Primeiros Passos",
        "icon": "bi-rocket-takeoff",
        "description": "Entrar no sistema, navegar e entender a interface.",
        "audience": "user",
        "article_ids": ["o-que-e-o-sistema", "entrar-e-sair", "conhecendo-a-interface"],
    },
    {
        "key": "patrimonio",
        "title": "Patrimônio & Equipamentos",
        "icon": "bi-laptop",
        "description": "Cadastrar, consultar e importar os bens do acervo.",
        "audience": "user",
        "article_ids": ["cadastrar-equipamento", "consultar-equipamentos", "detalhes-do-bem",
                        "etiquetas-patrimoniais", "importar-equipamentos", "corrigir-informacoes"],
    },
    {
        "key": "movimentacao",
        "title": "Fluxo & Movimentação",
        "icon": "bi-arrow-left-right",
        "description": "Entregas, transferências, devoluções e baixas.",
        "audience": "user",
        "article_ids": ["movimentar-equipamento", "tipos-de-movimentacao", "historico-do-bem"],
    },
    {
        "key": "manutencao",
        "title": "Manutenções",
        "icon": "bi-wrench",
        "description": "Ordens de serviço e reparos de equipamentos.",
        "audience": "user",
        "article_ids": ["abrir-ordem-servico", "finalizar-manutencao"],
    },
    {
        "key": "inventarios",
        "title": "Inventários",
        "icon": "bi-clipboard-check",
        "description": "Conferência física do acervo, com ata comprobatória.",
        "audience": "user",
        "article_ids": ["inventarios-overview", "conferir-inventario"],
    },
    {
        "key": "colaboradores",
        "title": "Colaboradores & Locais",
        "icon": "bi-people",
        "description": "Custodiantes, departamentos e localizações físicas.",
        "audience": "user",
        "article_ids": ["cadastrar-colaboradores", "cadastrar-locais"],
    },
    {
        "key": "relatorios",
        "title": "Relatórios & Exportações",
        "icon": "bi-file-earmark-text",
        "description": "Inventário, trilha de auditoria e exportação em CSV.",
        "audience": "user",
        "article_ids": ["relatorios", "exportar-csv"],
    },
    {
        "key": "administracao",
        "title": "Administração",
        "icon": "bi-shield-lock",
        "description": "Usuários, perfis, permissões e auditoria.",
        "audience": "admin",
        "article_ids": ["gerenciar-usuarios", "perfis-e-permissoes", "integracao-active-directory", "auditoria"],
    },
]

# ============================================================================
# HELPERS
# ============================================================================

def get_articles() -> List[Dict]:
    """Todos os artigos, na ordem de exibição."""
    return ARTICLES


def get_article(article_id: str) -> Optional[Dict]:
    """Retorna um artigo pelo id, ou None."""
    for article in ARTICLES:
        if article["id"] == article_id:
            return article
    return None


def get_faq() -> List[Dict]:
    return FAQ


def get_categories() -> List[Dict]:
    """Categorias com os artigos correspondentes embutidos."""
    categories = []
    by_id = {a["id"]: a for a in ARTICLES}
    for cat in CATEGORIES:
        item = dict(cat)
        item["articles"] = [by_id[a_id] for a_id in cat.get("article_ids", []) if a_id in by_id]
        categories.append(item)
    return categories


def serialize_search_index() -> List[Dict]:
    """
    Índice leve para a busca no manual (client-side): id, título, módulo,
    resumo e o texto completo (títulos, corpos, passos e palavras-chave)
    de cada artigo, além das perguntas/respostas do FAQ.
    """
    def _full_text(article: Dict) -> str:
        parts = [article.get("title", ""), article.get("summary", "")]
        parts.extend(article.get("keywords", []))
        for section in article.get("sections", []):
            parts.append(section.get("heading", ""))
            parts.append(section.get("body", ""))
            parts.append(section.get("note", ""))
            parts.extend(section.get("steps", []))
        return " ".join(parts).lower()

    index = [
        {
            "id": a["id"],
            "title": a["title"],
            "module": a["module"],
            "summary": a["summary"],
            "text": _full_text(a),
            "type": "article",
        }
        for a in ARTICLES
    ]
    index.extend(
        {
            "id": f"faq-{i}",
            "title": f["question"],
            "module": "Perguntas Frequentes",
            "summary": f["answer"],
            "text": (f["question"] + " " + f["answer"]).lower(),
            "type": "faq",
        }
        for i, f in enumerate(FAQ)
    )
    return index