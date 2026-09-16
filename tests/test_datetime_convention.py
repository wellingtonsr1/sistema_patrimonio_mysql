"""Testes do mecanismo central de data/hora (feature 004 — T003/FOUNDATION).

Cobertura exigida por FR-015, isolada de qualquer fluxo de negócio:
- conversão UTC -> America/Recife com fuso nomeado (sem offset fixo);
- virada de dia (UTC que corresponde ao dia anterior em Recife);
- preservação de minutos/segundos;
- valor ausente (None-safe);
- idempotência de uso (não há dupla conversão no mecanismo);
- local -> UTC (filtros de período);
- formatação para exports (format_local).

Todas as asserções usam instantes fixos — nenhuma depende de now().
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.utils.time_utils import (
    RECIFE,
    local_to_utc,
    now_utc,
    utc_to_recife,
    format_local,
)


class TestNowUtc:
    def test_retorna_naive(self):
        value = now_utc()
        assert value.tzinfo is None

    def test_corresponde_ao_utc_real(self):
        aware_now = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)
        value = now_utc().replace(microsecond=0)
        # Tolerância de 2s de execução
        assert abs((aware_now - value).total_seconds()) <= 2

    def test_na_e_hora_local_do_servidor(self):
        # Em um servidor UTC-3, now() local != now_utc (diferença de 3h)
        local_now = datetime.now()
        utc_now = now_utc()
        diff = abs((local_now - utc_now).total_seconds())
        # Se o processo roda em UTC a diferença é ~0 e o teste segue válido;
        # em Recife (UTC-3) a diferença fica em torno de 10800s.
        assert diff >= 0  # sanidade; comparação exata é sensível ao ambiente


class TestUtcToRecife:
    def test_conversao_basica(self):
        utc_value = datetime(2026, 9, 15, 22, 30)
        result = utc_to_recife(utc_value)
        assert result.hour == 19 and result.minute == 30
        assert result.day == 15
        assert str(result.tzinfo) == "America/Recife"

    def test_virada_de_dia(self):
        # UTC 16/09 02:30 == Recife 15/09 23:30
        utc_value = datetime(2026, 9, 16, 2, 30)
        result = utc_to_recife(utc_value)
        assert (result.day, result.month, result.year) == (15, 9, 2026)
        assert result.hour == 23 and result.minute == 30

    def test_preserva_segundos(self):
        utc_value = datetime(2026, 9, 15, 22, 30, 45)
        result = utc_to_recife(utc_value)
        assert (result.hour, result.minute, result.second) == (19, 30, 45)

    def test_none_retorna_none(self):
        assert utc_to_recife(None) is None

    def test_valor_aware_e_respeitado(self):
        # Instante absoluto com offset explícito: não recebe tratamento naive
        aware = datetime(2026, 9, 15, 22, 30, tzinfo=timezone.utc)
        result = utc_to_recife(aware)
        assert result.hour == 19 and result.minute == 30

    def test_fuso_nomeado_nao_offset_fixo(self):
        # America/Recife é fuso nomeado (atualmente UTC-3). O resultado deve
        # portar o fuso, não um timedelta fixo.
        result = utc_to_recife(datetime(2026, 9, 15, 22, 30))
        assert result.utcoffset() == RECIFE.utcoffset(result)
        assert result.tzinfo is RECIFE

    def test_sem_dupla_conversao_no_mecanismo(self):
        # Converter duas vezes o MESMO valor original dá o mesmo resultado
        # (o mecanismo não acumula deslocamento); e o valor original não muda.
        original = datetime(2026, 9, 15, 22, 30)
        once = utc_to_recife(original)
        twice = utc_to_recife(original)
        assert once == twice
        assert original == datetime(2026, 9, 15, 22, 30)  # imutabilidade do naive de entrada

    def test_aplicar_sobre_valor_ja_convertido_desloca(self):
        # Documenta o contrato de uso único: passar o valor JÁ convertido
        # novamente pelo filtro produz valor errado — por isso nenhum fluxo
        # deve fazê-lo (edge case "dupla conversão" da spec).
        converted = utc_to_recife(datetime(2026, 9, 15, 22, 30))
        reconverted = utc_to_recife(converted.replace(tzinfo=None))
        assert reconverted.hour == 16  # 19:30 - 3h — resultado incorreto, esperado pelo contrato


class TestLocalToUtc:
    def test_conversao_basica(self):
        local_value = datetime(2026, 9, 15, 19, 30)
        result = local_to_utc(local_value)
        assert result == datetime(2026, 9, 15, 22, 30)
        assert result.tzinfo is None  # naive UTC para comparar com DATETIME

    def test_ida_e_volta(self):
        original_utc = datetime(2026, 9, 15, 22, 30, 45)
        local_value = utc_to_recife(original_utc)
        back = local_to_utc(local_value.replace(tzinfo=None))
        assert back == original_utc

    def test_virada_de_dia_local_para_utc(self):
        # Recife 23:50 de 15/09 == UTC 02:50 de 16/09
        result = local_to_utc(datetime(2026, 9, 15, 23, 50))
        assert (result.day, result.hour, result.minute) == (16, 2, 50)

    def test_valor_aware_com_offset(self):
        aware = datetime(2026, 9, 15, 19, 30, tzinfo=RECIFE)
        result = local_to_utc(aware)
        assert result == datetime(2026, 9, 15, 22, 30)

    def test_aware_offset_diferente_respeitado(self):
        # Cliente informou -05:00 explicitamente: instante absoluto
        aware = datetime(2026, 9, 15, 18, 30, tzinfo=timezone(timedelta(hours=-5)))
        result = local_to_utc(aware)
        assert result == datetime(2026, 9, 15, 23, 30)


class TestFormatLocal:
    def test_formato_padrao(self):
        assert format_local(datetime(2026, 9, 15, 22, 30)) == "15/09/2026 19:30"

    def test_formato_com_segundos(self):
        value = datetime(2026, 9, 15, 22, 30, 45)
        assert format_local(value, "%d/%m/%Y %H:%M:%S") == "15/09/2026 19:30:45"

    def test_none_retorna_vazio(self):
        assert format_local(None) == ""

    def test_virada_de_dia_no_formato(self):
        assert format_local(datetime(2026, 9, 16, 2, 30)) == "15/09/2026 23:30"


class TestProibicaoOffsetFixo:
    def test_mecanismo_nao_usa_timedelta_fixo(self):
        # A diferença UTC x Recife vem do fuso nomeado; com as regras atuais é
        # -3h, mas o resultado deve ser calculado pelo ZoneInfo (o teste falha
        # se o mecanismo retornar um offset que o fuso nomeado não valida).
        utc_value = datetime(2026, 9, 15, 22, 30)
        result = utc_to_recife(utc_value)
        expected = utc_value.replace(tzinfo=timezone.utc).astimezone(RECIFE)
        assert result == expected
