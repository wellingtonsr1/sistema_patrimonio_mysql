# Feature Specification: Documentação de cenários de rede (offline + Central de Ajuda)

**Feature Branch**: `060-doc-cenarios-rede`
**Created**: 2026-09-30
**Status**: Implemented

## Problema (situação real do usuário)

Ao desligar a rede da máquina servidora e ver a página "Você está offline", o usuário concluiu que o sistema "não funciona sem internet". Confusão entre três redes distintas (internet da operadora × rede local × servidor), documentada em nenhum lugar do produto.

## Requisitos funcionais

- **FR-001**: A página `offline-start.html` (fallback do PWA) MUST incluir a dica: no **próprio servidor**, com a rede desconectada, o sistema continua acessível por `https://localhost:8000` (sem necessidade de rede alguma).
- **FR-002**: A Central de Ajuda (`/ajuda`) MUST ganhar um artigo (módulo "Primeiros Passos", audiência `user`) explicando: internet da operadora × rede local (LAN) × servidor; os 3 cenários de queda (internet cai → nada muda; servidor fora → coleta preparada funciona e sincroniza depois; sem coleta preparada → preparar antes), e como acessar na própria máquina (`localhost:8000`).
- **FR-003**: O artigo MUST ser indexável pela pesquisa da Central de Ajuda (keywords cobrindo "internet", "offline", "rede", "servidor", "sem conexão", "localhost").
- **FR-004**: Nenhuma mudança de comportamento/rota/service — apenas conteúdo.

## Critérios de aceitação

- **SC-001**: `offline-start.html` contém a dica do localhost (teste estrutural).
- **SC-002**: Artigo presente no `help_service` (id estável), renderizável em `/ajuda/{id}`, com keywords no índice de pesquisa (teste via service).
- **SC-003**: Régua completa 100% verde.
