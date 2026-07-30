from langchain_core.tools import tool

from ...application.product_service import ProductService
from ...core.exceptions import NotFoundError


def build_catalog_tools(product_service: ProductService) -> list:
    """Construye las tools de LangChain para el agente de Catálogo/Ventas.

    Las tools quedan atadas (closure) a la instancia de ProductService recibida,
    que a su vez encapsula el ProductRepositoryPort correspondiente a la request.
    """

    @tool
    def buscar_producto(nombre_o_categoria: str) -> str:
        """Busca productos por nombre o categoría (coincidencia parcial).

        Args:
            nombre_o_categoria: texto a buscar en el nombre o descripción del producto.
        """
        productos = product_service.search_products(nombre_o_categoria)
        if not productos:
            return f"No se encontraron productos que coincidan con '{nombre_o_categoria}'."

        lineas = [
            f"id={p.id} | {p.name} | ${p.price} | stock={p.stock} | {p.description}"
            for p in productos
        ]
        return "\n".join(lineas)

    @tool
    def consultar_stock(product_id: int) -> str:
        """Consulta el stock disponible de un producto por su id.

        Args:
            product_id: id del producto a consultar.
        """
        producto = product_service.get_product_by_id(product_id)
        if not producto:
            return f"No existe un producto con id {product_id}."
        return f"El producto '{producto.name}' (id={producto.id}) tiene {producto.stock} unidades en stock."

    @tool
    def calcular_precio(product_id: int, cantidad: int, descuento_pct: float = 0) -> str:
        """Calcula el precio total de una compra, aplicando un descuento opcional.

        Args:
            product_id: id del producto.
            cantidad: cantidad de unidades a comprar.
            descuento_pct: porcentaje de descuento a aplicar (0-100). Por defecto 0.
        """
        try:
            resultado = product_service.calculate_price(
                product_id=product_id, cantidad=cantidad, descuento_pct=descuento_pct
            )
        except NotFoundError as exc:
            return exc.message

        return (
            f"Producto: {resultado['product_name']} (id={resultado['product_id']})\n"
            f"Precio unitario: ${resultado['unit_price']}\n"
            f"Cantidad: {resultado['cantidad']}\n"
            f"Descuento: {resultado['descuento_pct']}% (-${resultado['descuento']:.2f})\n"
            f"Total: ${resultado['total']:.2f}"
        )

    return [buscar_producto, consultar_stock, calcular_precio]
