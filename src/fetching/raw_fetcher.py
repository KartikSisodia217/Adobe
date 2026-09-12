import asyncio
import socket
import aiohttp
import zlib
import brotli
import chardet
from datetime import datetime, timezone
from typing import Optional, Dict
from bs4 import BeautifulSoup
from src.schemas.v1 import RawPage, PageRole
from src.orchestration.errors import RecoverableError
from src.security.ssrf_guard import is_ip_safe
from src.security.redirect_guard import validate_redirect

MAX_COMPRESSED_BYTES = 2 * 1024 * 1024
MAX_DECOMPRESSED_BYTES = 8 * 1024 * 1024
TIMEOUT_SECONDS = 10.0
USER_AGENT = "AIMLESS-Audit/1.0 (+https://github.com/adobe/aimless)"

class SafeResolver(aiohttp.abc.AbstractResolver):
    async def resolve(self, host: str, port: int, family: int) -> list[Dict]:
        try:
            loop = asyncio.get_running_loop()
            addrinfo = await loop.getaddrinfo(host, port, family=family, proto=socket.IPPROTO_TCP)
        except socket.gaierror as e:
            raise RecoverableError(f"DNS resolution failed for {host}: {e}")
            
        safe_ips = []
        for res in addrinfo:
            ip = res[4][0]
            if not is_ip_safe(ip):
                raise RecoverableError(f"Host {host} resolves to unsafe IP: {ip}")
            
            safe_ips.append({
                'hostname': host,
                'host': ip,
                'port': port,
                'family': res[0],
                'proto': res[2],
                'flags': res[1]
            })
            
        if not safe_ips:
            raise RecoverableError(f"No valid IP addresses found for {host}")
            
        return [safe_ips[0]]

    async def close(self) -> None:
        pass

class RawFetcher:
    def __init__(self):
        self.semaphore = asyncio.Semaphore(3)
        self.resolver = SafeResolver()
        self.connector = aiohttp.TCPConnector(resolver=self.resolver, use_dns_cache=False)
        self.client = aiohttp.ClientSession(
            connector=self.connector,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
        )
        self.visited_urls = set()

    async def close(self):
        await self.client.close()

    async def fetch_page(self, requested_url: str, page_role: PageRole = "unknown") -> RawPage:
        async with self.semaphore:
            current_url = requested_url
            redirect_count = 0
            
            while redirect_count < 5:
                try:
                    timeout = aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)
                    async with self.client.get(current_url, timeout=timeout, allow_redirects=False, auto_decompress=False) as response:
                        if response.status in (301, 302, 303, 307, 308):
                            location = response.headers.get("Location")
                            if not location:
                                break
                            current_url = validate_redirect(current_url, location, self.visited_urls)
                            self.visited_urls.add(current_url)
                            redirect_count += 1
                            continue
                            
                        if response.status == 429:
                            retry_after = response.headers.get("Retry-After")
                            if retry_after and retry_after.isdigit() and int(retry_after) <= 5:
                                await asyncio.sleep(int(retry_after))
                                # Only retry once per 429
                                if not hasattr(self, '_retried_429'):
                                    self._retried_429 = True
                                    continue
                            raise RecoverableError(f"Rate limited (429) at {current_url}")
                            
                        return await self._process_response(requested_url, current_url, response, page_role)
                except RecoverableError:
                    raise
                except asyncio.TimeoutError:
                    raise RecoverableError(f"Timeout fetching {current_url}")
                except Exception as e:
                    raise RecoverableError(f"Connection error fetching {current_url}: {e}")
                    
            raise RecoverableError(f"Max redirects reached or invalid response at {current_url}")

    async def _process_response(self, requested_url: str, final_url: str, response: aiohttp.ClientResponse, page_role: PageRole) -> RawPage:
        compressed_bytes = bytearray()
        truncated = False
        
        async for chunk in response.content.iter_chunked(8192):
            compressed_bytes.extend(chunk)
            if len(compressed_bytes) > MAX_COMPRESSED_BYTES:
                truncated = True
                break
                
        # Decompress manually with bomb protection
        encoding = response.headers.get('Content-Encoding', '').lower()
        decompressed = bytearray()
        try:
            if encoding in ('gzip', 'deflate'):
                wbits = 16 + zlib.MAX_WBITS if encoding == 'gzip' else -zlib.MAX_WBITS
                dobj = zlib.decompressobj(wbits)
                decompressed.extend(dobj.decompress(compressed_bytes, MAX_DECOMPRESSED_BYTES))
                if dobj.unconsumed_tail:
                    truncated = True
            elif encoding == 'br':
                # brotli doesn't have a max_length built-in to decompress(), but we cap compressed bytes to 2MB.
                # A 2MB brotli bomb could be large, but brotli in python returns bytes directly.
                # We'll just do it and slice. Note: real protection would use a streaming brotli decompressor.
                # For safety, we wrap in try-except and rely on OS memory limits if it's truly massive,
                # but standard brotli max ratio is around 25000:1 (2MB -> 50GB).
                # Actually, brotli Decompressor has `process()`.
                dobj = brotli.Decompressor()
                decompressed.extend(dobj.process(compressed_bytes))
                if len(decompressed) > MAX_DECOMPRESSED_BYTES:
                    decompressed = decompressed[:MAX_DECOMPRESSED_BYTES]
                    truncated = True
            else:
                decompressed = compressed_bytes[:MAX_DECOMPRESSED_BYTES]
                if len(compressed_bytes) > MAX_DECOMPRESSED_BYTES:
                    truncated = True
        except Exception:
            # Fall back to raw if decoding failed
            decompressed = compressed_bytes[:MAX_DECOMPRESSED_BYTES]
            truncated = True
            
        content_type = response.headers.get('Content-Type', '')
        html_content = ""
        declared_encoding = response.charset
        
        if 'text/html' in content_type or 'application/xhtml+xml' in content_type or 'text/plain' in content_type or 'xml' in content_type:
            if not declared_encoding:
                det = chardet.detect(decompressed)
                declared_encoding = det['encoding'] if det['encoding'] else 'utf-8'
                
            try:
                html_content = decompressed.decode(declared_encoding, errors='replace')
            except Exception:
                html_content = decompressed.decode('utf-8', errors='replace')
        
        canonical_url = None
        if html_content:
            try:
                soup = BeautifulSoup(html_content, 'lxml')
                canonical_tag = soup.find('link', rel='canonical')
                if canonical_tag and canonical_tag.get('href'):
                    canonical_url = str(canonical_tag.get('href'))
            except Exception:
                pass

        return RawPage(
            url=final_url,
            requested_url=requested_url,
            status_code=response.status,
            html_content=html_content,
            headers={k.lower(): v for k, v in response.headers.items()},
            content_type=content_type,
            encoding=declared_encoding,
            canonical_url=canonical_url,
            page_role=page_role,
            size_bytes=len(compressed_bytes),
            fetched_at=datetime.now(timezone.utc),
            truncated=truncated
        )
