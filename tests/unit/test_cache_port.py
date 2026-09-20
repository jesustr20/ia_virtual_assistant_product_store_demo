from app.domain.ports.cache_port import build_cache_key


def test_build_cache_key_normalizes_casing_and_whitespace():
    a = build_cache_key("catalogo", "Hola  Mundo")
    b = build_cache_key("catalogo", "hola mundo")
    c = build_cache_key("catalogo", "  HOLA   MUNDO ")

    assert a == b == c


def test_build_cache_key_differs_by_agent_prefix():
    key_catalogo = build_cache_key("catalogo", "hola")
    key_route = build_cache_key("route", "hola")

    assert key_catalogo != key_route


def test_build_cache_key_starts_with_agent_prefix():
    key = build_cache_key("route", "hola")

    assert key.startswith("route:")
