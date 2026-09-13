import os
import json

BASE_DIR = "tests/fixtures/generalization"

FIXTURES = {
    "A_static_conventional": {
        "index.html": "<html><head><title>Home</title></head><body><nav><a href='/about'>About</a></nav><h1>Welcome to our Company</h1><p>We do things.</p></body></html>",
        "about.html": "<html><head><title>About</title></head><body><h1>About Us</h1><p>Contact us at info@company.com</p></body></html>"
    },
    "B_spa_js": {
        "index.html": "<html><head><title>App</title><script>document.addEventListener('DOMContentLoaded', () => { document.body.innerHTML = '<h1>Dynamic Product</h1><p>Price: $99.99/month</p>'; });</script></head><body></body></html>"
    },
    "D_ecommerce": {
        "index.html": "<html><head><title>Shop</title></head><body><a href='/product/123'>Buy Item</a></body></html>",
        "product/123.html": "<html><head><title>Item 123</title></head><body><h1>Item 123</h1><p>$49.99</p><button>Add to cart</button></body></html>"
    },
    "E_documentation": {
        "index.html": "<html><head><title>Docs</title></head><body><a href='/docs/getting-started'>Start</a></body></html>",
        "docs/getting-started.html": "<html><head><title>Getting Started</title></head><body><h1>Install</h1><p>npm install</p></body></html>"
    },
    "F_university": {
        "index.html": "<html><head><title>University</title></head><body><a href='/admissions'>Apply</a><a href='/departments'>Departments</a></body></html>"
    },
    "G_news": {
        "index.html": "<html><head><title>News</title></head><body><a href='/article/1'>Breaking News</a></body></html>",
        "article/1.html": "<html><head><title>Breaking News</title></head><body><h1>News Title</h1><p>Content here.</p></body></html>"
    },
    "H_unusual_nav": {
        "index.html": "<html><head><title>Odd Nav</title></head><body><div role='navigation'><span role='link' onclick='location.href=\"/page2\"' tabindex='0'>Go</span></div></body></html>",
        "page2.html": "<html><body><h1>Page 2</h1></body></html>"
    },
    "K_valid_jsonld_no_conflict": {
        "index.html": "<html><head><title>Item</title><script type='application/ld+json'>{\"@type\":\"Product\",\"name\":\"Item\",\"offers\":{\"price\":\"10.00\",\"priceCurrency\":\"USD\"}}</script></head><body><h1>Item</h1><p>$10.00</p></body></html>"
    },
    "L_visible_vs_structured_conflict": {
        "index.html": "<html><head><title>Item</title><script type='application/ld+json'>{\"@type\":\"Product\",\"name\":\"Item\",\"offers\":{\"price\":\"10.00\",\"priceCurrency\":\"USD\"}}</script></head><body><h1>Item</h1><p>$20.00</p></body></html>"
    },
    "O_unnamed_controls": {
        "index.html": "<html><body><button></button><a href='/'></a></body></html>"
    },
    "P_blocking_modal_working_exit": {
        "index.html": "<html><body><div role='dialog' aria-modal='true'><h1>Modal</h1><button>Close</button></div></body></html>"
    },
    "Q_trapping_modal": {
        "index.html": "<html><body><div role='dialog' aria-modal='true'><h1>Modal</h1><button>Fake Close</button></div></body></html>"
    },
    "T_robots_restrict": {
        "robots.txt": "User-agent: *\nDisallow: /private/\nSitemap: /sitemap.xml",
        "sitemap.xml": "<?xml version='1.0'?><urlset><url><loc>http://localhost:9999/public</loc></url></urlset>",
        "public.html": "<html><body>Public</body></html>",
        "private/index.html": "<html><body>Private</body></html>"
    }
}

os.makedirs(BASE_DIR, exist_ok=True)
for fix_name, files in FIXTURES.items():
    fix_dir = os.path.join(BASE_DIR, fix_name)
    os.makedirs(fix_dir, exist_ok=True)
    for fname, content in files.items():
        fpath = os.path.join(fix_dir, fname)
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        with open(fpath, "w") as f:
            f.write(content)

print(f"Generated {len(FIXTURES)} generalization fixtures.")
