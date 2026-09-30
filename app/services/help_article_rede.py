"""Artigo da Central de Ajuda — Internet × rede local × servidor (feature 060).

Padrão help_article_030/031/032/045: conteúdo concentrado, importado por
`help_service` e integrado à Central de Ajuda (/ajuda).
"""
from typing import Dict

ARTIGO_CENARIOS_REDE: Dict = {
    "id": "internet-rede-servidor",
    "title": "Internet × rede local × servidor (o sistema funciona sem internet?)",
    "module": "Primeiros Passos",
    "icon": "bi-router",
    "audience": "user",
    "summary": "Entenda do que o sistema realmente precisa: a internet da operadora é opcional — o que importa é a rede local até o servidor (ou a coleta offline preparada antes).",
    "keywords": [
        "internet", "sem internet", "offline", "coleta offline", "rede", "rede local",
        "lan", "servidor", "sem conexão", "sem conexao", "localhost", "você está offline",
        "voce esta offline", "caiu a internet", "wi-fi", "wifi", "cabo", "modem",
        "não abre", "nao abre", "preparar coleta",
    ],
    "sections": [
        {
            "heading": "As três redes — qual é qual",
            "body": (
                "1. INTERNET (operadora/modem): o sistema NÃO depende dela. Nenhuma tela, fonte ou "
                "biblioteca vem da internet — tudo é servido pelo próprio servidor.\\n\\n"
                "2. REDE LOCAL (Wi-Fi/cabo da instituição): é o caminho entre os computadores/celulares "
                "e o servidor. Por ela o navegador acessa https://10.39.0.16:8000.\\n\\n"
                "3. SERVIDOR: a máquina onde o sistema e o banco de dados moram. É ele quem \"é\" o sistema."
            ),
        },
        {
            "heading": "O que acontece em cada queda",
            "steps": [
                "Caiu a INTERNET (operadora): nada muda — continue trabalhando normalmente (PC e celulares pela rede local).",
                "Caiu a REDE LOCAL (roteador/switch) ou o cabo de um aparelho: esse aparelho perde o acesso até reconectar; os demais continuam.",
                "O SERVIDOR reiniciou ou está desligado: navegação indisponível por definição (os dados estão nele) — MAS a coleta offline preparada antes continua funcionando no aparelho e sincroniza sozinha quando o servidor volta.",
            ],
            "note": "A tela \"Você está offline\" do app instalado indica ausência do SERVIDOR (não da internet) e, se houver coleta preparada neste dispositivo, oferece o botão \"Abrir última coleta\".",
        },
        {
            "heading": "Estou na própria máquina do servidor, sem rede nenhuma",
            "steps": [
                "Abra https://localhost:8000 no navegador da máquina servidora.",
                "localhost não precisa de rede (nem Wi-Fi, nem cabo) — o navegador fala com a própria máquina.",
                "O sistema abre completo: login, dashboard, gráficos, etiquetas, conferência.",
            ],
        },
        {
            "heading": "Como trabalhar em campo sem servidor ao alcance",
            "steps": [
                "Ainda na rede: login → Inventários → abrir o inventário → \"Preparar coleta offline\".",
                "Em campo sem rede: abrir o app instalado → \"Abrir última coleta\" → conferir bens (câmera/QR funcionam; tudo gravado no aparelho).",
                "De volta à rede: as coletas sincronizam automaticamente com o servidor.",
            ],
            "note": "A coleta offline precisa ser preparada ANTES de sair da rede — é ela que baixa a lista de bens para o aparelho.",
        },
    ],
    "related": ["coleta-offline-inventario", "o-que-e-o-sistema"],
}
