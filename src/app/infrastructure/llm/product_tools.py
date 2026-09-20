from langchain_core.tools import BaseTool, tool

from ...application.product_service import ProductService
from ...core.exceptions import NotFoundError
from ...domain.ports.vector_store_port import VectorStorePort


def build_catalog_tools(
    product_service: ProductService, vector_store: VectorStorePort
) -> dict[str, BaseTool]:
    """Construye TODAS las tools de LangChain del agente de Catálogo/Ventas.

    Devuelve un dict `{nombre: tool}` con las implementaciones definidas acá. Cuáles
    llegan efectivamente al agente lo decide el registro de capacidades
    (`core/security/agent_capabilities.py`, issue #23): si acá se define una tool nueva
    pero no se la registra, no se expone al agente (ver `build_catalog_agent`).

    Las tools quedan atadas (closure) a la instancia de ProductService y al
    VectorStorePort recibidos, que a su vez encapsulan el ProductRepositoryPort
    y el backend de vectores correspondientes a la request.
    """

    @tool
    def buscar_producto(consulta: str) -> str:
        """Busca productos por similitud semántica a partir de una consulta en lenguaje natural.

        La búsqueda no requiere coincidencia textual exacta con el nombre del producto:
        encuentra productos relacionados por significado (ej. "calzado deportivo para
        correr" puede encontrar "Zapatillas Running Pro").

        Args:
            consulta: descripción de lo que el usuario busca.
        """
        resultados = vector_store.search(consulta, k=5)
        if not resultados:
            return f"No se encontraron productos relacionados con '{consulta}'."

        lineas = []
        for resultado in resultados:
            product_id = resultado.metadata.get("product_id")
            producto = (
                product_service.get_product_by_id(product_id) if product_id is not None else None
            )
            if producto:
                lineas.append(
                    f"id={producto.id} | {producto.name} | ${producto.price} | "
                    f"stock={producto.stock} | {producto.description}"
                )
            else:
                lineas.append(f"id={product_id} | {resultado.text}")
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

    all_tools = [buscar_producto, consultar_stock, calcular_precio]
    return {tool.name: tool for tool in all_tools}

