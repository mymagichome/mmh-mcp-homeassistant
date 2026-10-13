"""Tool registry unit tests."""

from __future__ import annotations

import pytest

from custom_components.mmh_mcp import registry as reg_mod
from custom_components.mmh_mcp.registry import ToolDef, paginate, schema


def test_paginate_basic() -> None:
    items = list(range(10))
    out = paginate(items, limit=3, offset=4)
    assert out["items"] == [4, 5, 6]
    assert out["total"] == 10
    assert out["has_more"] is True
    assert out["next_offset"] == 7


def test_paginate_exhausted() -> None:
    out = paginate([1, 2], limit=10, offset=0)
    assert out["items"] == [1, 2]
    assert out["has_more"] is False
    assert out["next_offset"] is None


def test_schema_builder() -> None:
    s = schema(
        properties={"x": {"type": "string"}},
        required=["x"],
    )
    assert s["type"] == "object"
    assert s["additionalProperties"] is False
    assert s["required"] == ["x"]
    assert s["properties"] == {"x": {"type": "string"}}


def test_tool_decorator_registers(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_tools: dict[str, ToolDef] = {}
    monkeypatch.setattr(reg_mod, "TOOLS", fake_tools)

    @reg_mod.tool(
        name="ut_test",
        description="unit test",
        input_schema=schema(),
        read_only=True,
    )
    async def handler(hass):
        return {"ok": True}

    assert "ut_test" in fake_tools
    t = fake_tools["ut_test"]
    assert t.annotations["readOnlyHint"] is True
    listing = t.to_listing()
    assert listing["name"] == "ut_test"
    assert listing["inputSchema"]["type"] == "object"


def test_tool_decorator_rejects_duplicate(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_tools: dict[str, ToolDef] = {}
    monkeypatch.setattr(reg_mod, "TOOLS", fake_tools)

    @reg_mod.tool(name="dup", description="x", input_schema=schema())
    async def a(hass):
        return None

    with pytest.raises(ValueError):

        @reg_mod.tool(name="dup", description="x", input_schema=schema())
        async def b(hass):
            return None


def test_listing_publishes_mmh_permissions(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_tools: dict[str, ToolDef] = {}
    monkeypatch.setattr(reg_mod, "TOOLS", fake_tools)

    @reg_mod.tool(
        name="ut_meta",
        description="x",
        input_schema=schema(),
        read_only=False,
        requires_admin=True,
        write_ops=["update"],
        destructive_ops=["remove", "delete"],
        admin_ops=["logs"],
    )
    async def handler(hass):
        return None

    @reg_mod.tool(name="ut_svc", description="x", input_schema=schema(), requires_write=True)
    async def svc(hass):
        return None

    perms = fake_tools["ut_meta"].to_listing()["_meta"]["br.com.mymagichome/permissions"]
    assert perms == {
        "class": "read",
        "write_ops": ["update"],
        "destructive_ops": ["delete", "remove"],
        "admin_ops": ["logs"],
        "requires_admin": True,
        "requires_fire_event": False,
    }
    svc_perms = fake_tools["ut_svc"].to_listing()["_meta"]["br.com.mymagichome/permissions"]
    assert svc_perms["class"] == "write"
