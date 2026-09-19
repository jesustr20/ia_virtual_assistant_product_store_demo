from pydantic import BaseModel, Field


class VectorSearchResult(BaseModel):
    """Un resultado de búsqueda semántica devuelto por un VectorStorePort."""

    id: str = Field(description="Identificador del documento indexado (ej: product id como string)")
    text: str = Field(description="Texto original que fue indexado")
    metadata: dict = Field(
        default_factory=dict,
        description="Metadata asociada al documento (ej: {'product_id': 1, 'name': '...'})",
    )
    score: float | None = Field(
        default=None,
        description="Distancia/score de similitud devuelto por el backend (menor = más similar)",
    )
