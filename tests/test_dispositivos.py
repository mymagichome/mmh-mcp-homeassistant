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


def test_normalizar_entidade_converte_enums_e_conjuntos():
    from homeassistant.helpers import entity_registry as er

    from custom_components.mmh_mcp.tools.registries import _normalizar_entidade

    d = _normalizar_entidade(
        {"hidden_by": "user", "disabled_by": None, "labels": ["a"], "name": "X"}
    )
    assert d["hidden_by"] is er.RegistryEntryHider.USER
    assert d["disabled_by"] is None
    assert d["labels"] == {"a"}
    assert d["name"] == "X"


def test_normalizar_entidade_valor_invalido():
    import pytest

    from custom_components.mmh_mcp.protocol import ToolError
    from custom_components.mmh_mcp.tools.registries import _normalizar_entidade

    with pytest.raises(ToolError):
        _normalizar_entidade({"hidden_by": "qualquer"})


def test_normalizar_dispositivo():
    from homeassistant.helpers import device_registry as dr

    from custom_components.mmh_mcp.tools.registries import _normalizar_dispositivo

    d = _normalizar_dispositivo({"disabled_by": "user", "labels": ["x"]})
    assert d["disabled_by"] is dr.DeviceEntryDisabler.USER
    assert d["labels"] == {"x"}
