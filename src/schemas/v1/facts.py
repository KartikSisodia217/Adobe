from typing import Literal, Optional, Dict
from pydantic import BaseModel, HttpUrl

FactType = Literal[
    "organization_name", "person_name", "product_name", "course_name",
    "price", "availability", "article_title", "contact", "official_domain",
    "destination", "description", "social_link", "same_as"
]
FactSource = Literal["raw_html", "json_ld", "meta_tag", "noscript", "rendered_only", "external"]

class StructuredFact(BaseModel):
    fact_type: FactType
    value: str
    source: FactSource
    page_url: HttpUrl
    entity: str = "Unknown"
    entity_type: str = "general" # organization, person, product, course, offer
    entity_subject: str = "Unknown" # exact subject e.g. "Full Stack Cohort"
    relationship: str = "none" # founded_by, offers, represented_by, variant_of
    currency: str = "Unknown"
    billing_period: str = "one-time" # e.g. monthly, yearly, one-time
    offer_type: str = "Unknown" # e.g. MSRP, Sale, Standard
    price_qualifier: str = "current" # current, original, promotional, starting_at
    metadata: Dict = {}
