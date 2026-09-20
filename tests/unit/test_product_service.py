from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.application.product_service import ProductService
from app.core.exceptions import NotFoundError


def _product(id: int, name: str, price: float) -> SimpleNamespace:
    return SimpleNamespace(id=id, name=name, price=price)


def test_calculate_price_computes_subtotal_discount_and_total():
    repo = Mock()
    repo.get_products_by_id.return_value = _product(1, "Zapatillas", 100.0)
    service = ProductService(repo)

    result = service.calculate_price(product_id=1, cantidad=3, descuento_pct=10)

    assert result["subtotal"] == 300.0
    assert result["descuento"] == 30.0
    assert result["total"] == 270.0
    assert result["product_id"] == 1
    assert result["product_name"] == "Zapatillas"
    assert result["unit_price"] == 100.0
    assert result["cantidad"] == 3
    assert result["descuento_pct"] == 10


def test_calculate_price_defaults_to_zero_discount():
    repo = Mock()
    repo.get_products_by_id.return_value = _product(2, "Termo", 50.0)
    service = ProductService(repo)

    result = service.calculate_price(product_id=2, cantidad=2)

    assert result["descuento_pct"] == 0
    assert result["descuento"] == 0.0
    assert result["total"] == 100.0


def test_calculate_price_raises_not_found_for_missing_product():
    repo = Mock()
    repo.get_products_by_id.return_value = None
    service = ProductService(repo)

    with pytest.raises(NotFoundError):
        service.calculate_price(product_id=999, cantidad=1)
