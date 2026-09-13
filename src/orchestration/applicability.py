from enum import Enum
from src.schemas.v1 import RawPage, RenderedPage

class Applicability(Enum):
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNCERTAIN = "UNCERTAIN"

def detector_applicability(page: RawPage | RenderedPage, detector: str) -> Applicability:
    role = page.page_role
    
    if detector == "D-02":
        if role in ["detail", "pricing"]: return Applicability.APPLICABLE
        if role in ["contact", "about"]: return Applicability.NOT_APPLICABLE
        return Applicability.UNCERTAIN
        
    if detector == "F-01":
        if role in ["editorial", "article", "blog"]: return Applicability.APPLICABLE
        if role in ["contact"]: return Applicability.NOT_APPLICABLE
        return Applicability.UNCERTAIN
        
    if detector == "E-02":
        if role in ["detail", "editorial"]: return Applicability.APPLICABLE
        return Applicability.UNCERTAIN
        
    if detector in ["G-02", "G-03"]:
        return Applicability.APPLICABLE
        
    if detector == "brand_identity":
        if role in ["landing", "about", "contact"]: return Applicability.APPLICABLE
        return Applicability.UNCERTAIN
        
    return Applicability.UNCERTAIN
