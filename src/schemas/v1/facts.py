from typing import Literal
from pydantic import BaseModel, HttpUrl

FactType = Literal["organization_name", "product_name", "price", "availability", "article_title", "contact"]
FactSource = Literal["raw_html", "json_ld", "meta_tag", "noscript", "rendered_only"]

class StructuredFact(BaseModel):
    fact_type: FactType
    value: str
    source: FactSource
    page_url: HttpUrl
    entity: str = "Unknown"
    currency: str = "Unknown"
    metadata: dict = {}
