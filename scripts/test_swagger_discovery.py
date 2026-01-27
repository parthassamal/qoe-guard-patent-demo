#!/usr/bin/env python3
"""
Test script to debug Swagger UI discovery.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import re
from urllib.parse import urljoin, urlparse

def test_swagger_discovery(url):
    """Test discovery of OpenAPI spec from Swagger UI URL."""
    print(f"Testing discovery for: {url}")
    print("=" * 70)
    
    try:
        # Fetch the HTML page
        print("\n1. Fetching HTML page...")
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        print(f"   Status: {resp.status_code}")
        print(f"   Content-Type: {resp.headers.get('content-type', 'unknown')}")
        print(f"   Content Length: {len(resp.text)} bytes")
        
        # Check if it's HTML
        if "html" not in resp.headers.get("content-type", "").lower():
            print("   ⚠️  Not an HTML page")
            return
        
        # Try to find spec URL in HTML
        print("\n2. Searching HTML for OpenAPI spec URL...")
        html = resp.text
        
        # Look for common patterns
        patterns = [
            (r'url:\s*["\']([^"\']+\.json)["\']', "url: '...json'"),
            (r'url:\s*["\']([^"\']+/openapi)["\']', "url: '...openapi'"),
            (r'url:\s*["\']([^"\']+/swagger)["\']', "url: '...swagger'"),
            (r'url:\s*["\']([^"\']+api-docs[^"\']*)["\']', "url: '...api-docs'"),
            (r'url:\s*["\']([^"\']+v3/api-docs[^"\']*)["\']', "url: '...v3/api-docs'"),
            (r'SwaggerUIBundle\s*\(\s*\{[^}]*url:\s*["\']([^"\']+)["\']', "SwaggerUIBundle url"),
            (r'urls:\s*\[\s*\{[^}]*url:\s*["\']([^"\']+)["\']', "urls: [{ url: ... }]"),
        ]
        
        found_urls = []
        for pattern, desc in patterns:
            matches = re.finditer(pattern, html, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                spec_url = match.group(1)
                if not spec_url.startswith(("http://", "https://")):
                    spec_url = urljoin(url, spec_url)
                if spec_url not in found_urls:
                    found_urls.append(spec_url)
                    print(f"   ✓ Found ({desc}): {spec_url}")
        
        if not found_urls:
            print("   ✗ No spec URLs found in HTML")
        
        # Try common paths
        print("\n3. Trying common OpenAPI paths...")
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Extract parent path from swagger-ui
        if "swagger-ui" in parsed_url.path:
            path_parts = [p for p in parsed_url.path.split("/") if p and "swagger-ui" not in p and "index.html" not in p]
            parent_path = "/" + "/".join(path_parts) if path_parts else ""
            if parent_path and not parent_path.endswith("/"):
                parent_path += "/"
        else:
            parent_path = "/"
        
        common_paths = [
            f"{parent_path}v3/api-docs",
            f"{parent_path}api/v3/api-docs",
            f"{parent_path}openapi.json",
            f"{parent_path}swagger.json",
            "/api/v3/api-docs",
            "/v3/api-docs",
        ]
        
        for path in common_paths:
            test_url = urljoin(base_url, path)
            try:
                test_resp = requests.get(test_url, timeout=10)
                if test_resp.status_code == 200:
                    try:
                        spec = test_resp.json()
                        if "openapi" in spec or "swagger" in spec:
                            print(f"   ✓ Found spec at: {test_url}")
                            print(f"      OpenAPI version: {spec.get('openapi', spec.get('swagger', 'unknown'))}")
                            print(f"      Title: {spec.get('info', {}).get('title', 'N/A')}")
                            return test_url
                    except:
                        pass
            except:
                pass
        
        print("   ✗ No valid spec found at common paths")
        
        # Show HTML snippet for debugging
        print("\n4. HTML snippet (first 2000 chars):")
        print("-" * 70)
        print(html[:2000])
        print("-" * 70)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://api-web-pplus-us-test-www.app-dev-usc1.paramountplus.com/api/swagger-ui/index.html"
    test_swagger_discovery(url)
