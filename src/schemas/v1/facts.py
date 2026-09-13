from typing import Literal
from pydantic import BaseModel, HttpUrl

FactType = Literal["organization_name", "product_name", "price", "availability", "article_title", "contact", "official_domain", "destination", "description"]
FactSource = Literal["raw_html", "json_ld", "meta_tag", "noscript", "rendered_only"]

class StructuredFact(BaseModel):
    fact_type: FactType
    value: str
    source: FactSource
    page_url: HttpUrl
    entity: str = "Unknown"
    currency: str = "Unknown"
    billing_period: str = "one-time" # e.g. monthly, yearly, one-time
    offer_type: str = "Unknown" # e.g. MSRP, Sale, Standard
    metadata: dict = {}
