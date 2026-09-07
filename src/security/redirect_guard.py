from urllib.parse import urljoin
from src.orchestration.errors import RecoverableError
from .url_normalize import normalize_url

def validate_redirect(current_url: str, location_header: str, visited_urls: set) -> str:
    if len(visited_urls) >= 5:
        raise RecoverableError(f"Maximum redirect hops (5) exceeded at {current_url}")
        
    next_url = urljoin(current_url, location_header)
    
    # Normalizes and checks for unsafe schemes/localhost strings
    try:
        normalized_next, _ = normalize_url(next_url, allow_http=True)
    except Exception as e:
        raise RecoverableError(f"Redirected to unsafe/invalid URL {next_url}: {e}")
        
    if normalized_next in visited_urls:
        raise RecoverableError(f"Redirect loop detected at {normalized_next}")
        
    return normalized_next
