"""Leitura do registro de dispositivos compatível com HA antigo e recente."""

from types import SimpleNamespace

from custom_components.mmh_mcp.tools.registries import (
    _entradas_do_dispositivo,
    todos_dispositivos,
)


class _Itens:
    """HA recente: iterar devolve os DeviceEntry."""

    def __init__(self, entradas):
        self._e = entradas

    def __iter__(self):
        return iter(self._e)


def test_todos_dispositivos_ha_recente():
    a, b = SimpleNamespace(id="a"), SimpleNamespace(id="b")
    reg = SimpleNamespace(devices=_Itens([a, b]))
    assert todos_dispositivos(reg) == [a, b]


def test_todos_dispositivos_ha_antigo():
    a = SimpleNamespace(id="a")
    reg = SimpleNamespace(devices={"a": a})
    assert todos_dispositivos(reg) == [a]


def test_todos_dispositivos_vazio():
    assert todos_dispositivos(SimpleNamespace(devices={})) == []


def test_entradas_do_dispositivo():
    assert _entradas_do_dispositivo(SimpleNamespace(config_entry_id="x")) == ["x"]
    assert _entradas_do_dispositivo(SimpleNamespace(config_entry_id=None)) == []
    assert _entradas_do_dispositivo(SimpleNamespace(config_entries={"b", "a"})) == ["a", "b"]
