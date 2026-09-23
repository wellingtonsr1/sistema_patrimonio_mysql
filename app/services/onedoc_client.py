"""Cliente da integração 1Doc (feature 031 — contracts §4 / research D3-D4).

Protocolo ``OneDocProvider`` (implementável por fake nos testes — nunca HTTP
real na suíte) + implementação HTTP ``OneDocHttpClient`` via ``requests``
(dependência existente — zero dependências novas, F2).

**[PENDING C-1..C-4]** — os endpoints/paths/payloads REAIS NÃO são inventados
(spec §8 / input do usuário). A estrutura abaixo (autenticação por header,
timeouts, classificação de erros, sanitização) está pronta; os pontos de
conexão marcados ``[PENDING C-*]`` serão preenchidos quando o fornecedor
confirmar o contrato real. Enquanto isso, ``ONEDOC_ENABLED`` permanece ``false``.

Contrato do protocolo:
- ``find_process(process_number) -> bool | None`` — False=inexistente,
  None=não suportado/indisponível (decisão Q2: modo tolerante);
- ``send_communication(process_number, subject, body_text, body_html) -> str | None``
  — id da mensagem criada; None = não informado (decisão Q3: sucesso sem ID
  continua SENT).
"""

import logging
from typing import Optional, Protocol

import requests

from app import config

logger = logging.getLogger(__name__)


class OneDocError(Exception):
    """Erro de integração com o 1Doc (mensagem já sanitizada)."""


class OneDocTransientError(OneDocError):
    """Erro transitório (timeout, conexão, 5xx) — permite retry com limite (FR-010)."""


class OneDocPermanentError(OneDocError):
    """Erro permanente (4xx, credencial, autorização, dados inválidos) — sem retry (FR-010)."""


class OneDocProvider(Protocol):
    """Contrato mínimo do provedor 1Doc (contracts §4)."""

    def find_process(self, process_number: str) -> Optional[bool]:
        """False = inexistente; None = não suportado/indisponível (Q2)."""
        ...

    def send_communication(
        self,
        process_number: str,
        *,
        subject: str,
        body_text: str,
        body_html: str,
    ) -> Optional[str]:
        """Envia a comunicação; retorna id da mensagem (None = não informado — Q3)."""
        ...


def _sanitize_error(message: str) -> str:
    """Remove credenciais/token/URL do texto de erro (Constitution VI — precedente 030)."""
    for secret in (config.ONEDOC_API_TOKEN, config.ONEDOC_API_URL):
        if secret and secret in message:
            message = message.replace(secret, "***")
    return message


def _classify(status_code: Optional[int], exc: Optional[Exception]) -> OneDocError:
    """Classifica falha HTTP em transitória (5xx/None) × permanente (4xx) — FR-010."""
    if status_code is not None and 400 <= status_code < 500:
        return OneDocPermanentError(f"Erro permanente da API 1Doc (HTTP {status_code}).")
    if status_code is not None:
        return OneDocTransientError(f"Erro transitório da API 1Doc (HTTP {status_code}).")
    return OneDocTransientError(f"Erro de conexão com a API 1Doc: {type(exc).__name__ if exc else 'desconhecido'}")


class OneDocHttpClient:
    """Implementação HTTP via requests — [PENDING C-1..C-4]: nenhum endpoint inventado.

    A estrutura (sessão com header de autenticação, timeouts de config,
    classificação e sanitização de erros) está pronta. Os métodos levantam
    ``OneDocPermanentError`` informativa enquanto o contrato real não chega —
    com ``ONEDOC_ENABLED=false`` (default) este código NUNCA é alcançado.
    """

    def __init__(self) -> None:
        if not config.ONEDOC_API_URL or not config.ONEDOC_API_TOKEN:
            raise OneDocPermanentError(
                "Integração 1Doc não configurada (ONEDOC_API_URL/ONEDOC_API_TOKEN ausentes). "
                "A integração permanece inoperante até o contrato do fornecedor (C-1..C-4)."
            )
        self._session = requests.Session()
        # [PENDING C-1] — formato exato do header definido pelo fornecedor.
        self._session.headers.update(
            {
                "Authorization": f"Bearer {config.ONEDOC_API_TOKEN}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def _timeout(self) -> tuple:
        return (config.ONEDOC_CONNECT_TIMEOUT, config.ONEDOC_READ_TIMEOUT)

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """Executa requisição com classificação/sanitização de erros.

        [PENDING C-2/C-4] — ``path``/payload reais são conectados aqui quando
        o contrato chegar. Nenhuma rota é presumida hoje.
        """
        url = f"{config.ONEDOC_API_URL.rstrip('/')}{path}"
        try:
            response = self._session.request(method, url, timeout=self._timeout(), **kwargs)
        except (requests.Timeout, requests.ConnectionError) as exc:
            raise _classify(None, exc) from exc

        if response.status_code >= 400:
            raise _classify(response.status_code, None)
        try:
            return response.json()
        except ValueError as exc:
            raise OneDocPermanentError("Resposta não-JSON da API 1Doc.") from exc

    def find_process(self, process_number: str) -> Optional[bool]:
        """[PENDING C-2/C-3] — consulta de processo pelo identificador.

        Retorna False (inexistente) / True (existe) / None (não suportado).
        Enquanto C-2/C-3 não são confirmados, devolve None (modo tolerante
        da decisão Q2) para nunca bloquear movimentações por capacidades
        desconhecidas da API.
        """
        logger.info(
            "1Doc find_process pendente do contrato do fornecedor (C-2/C-3) — modo tolerante."
        )
        return None

    def send_communication(
        self,
        process_number: str,
        *,
        subject: str,
        body_text: str,
        body_html: str,
    ) -> Optional[str]:
        """[PENDING C-4] — inclusão da comunicação no processo.

        Enquanto C-4 não é confirmado, levanta erro permanente informativo
        (o estado FAILED resultante é registrável/reprocessável — US2/US3).
        Payload/texto-vs-HTML serão escolhidos conforme o formato aceito (C-4).
        """
        raise OneDocPermanentError(
            "Envio ao 1Doc pendente do contrato do fornecedor (C-4). "
            "Nenhum endpoint foi inventado; conecte o payload real quando confirmado."
        )
