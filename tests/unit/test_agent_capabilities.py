from unittest.mock import Mock

from app.core.security.agent_capabilities import (
    allowed_tool_names,
    select_allowed_tools,
)
from app.infrastructure.llm.product_tools import build_catalog_tools


def test_catalog_agent_allowed_tool_names_is_exact_set():
    assert allowed_tool_names("catalogo") == frozenset(
        {"buscar_producto", "consultar_stock", "calcular_precio"}
    )


def test_catalog_agent_receives_exactly_registered_tools():
    available = build_catalog_tools(Mock(), Mock())
    selected = select_allowed_tools("catalogo", available)

    assert {tool.name for tool in selected} == {
        "buscar_producto",
        "consultar_stock",
        "calcular_precio",
    }


def test_unregistered_tool_does_not_reach_agent():
    available = build_catalog_tools(Mock(), Mock())
    available["crear_orden"] = object()

    selected = select_allowed_tools("catalogo", available)

    assert "crear_orden" not in {tool.name for tool in selected}


def test_unknown_agent_has_no_tools():
    available = build_catalog_tools(Mock(), Mock())

    assert select_allowed_tools("soporte", available) == []
    assert select_allowed_tools("ventas", available) == []
