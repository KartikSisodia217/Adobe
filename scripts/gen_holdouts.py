import os

base_dir = 'tests/generalization/holdout'
os.makedirs(base_dir, exist_ok=True)

fixtures = {
    # D-01: unusual robots syntax
    'd01_unusual_robots': {'robots.txt': 'User-agent: OAI-SearchBot\nCrawl-delay: 10\nDisallow: /private\nDisallow: /'},
    
    # D-02: same-entity conflicting price
    'd02_same_entity': {
        'index.html': '<h1>Special Plan</h1><span itemprop="price">99.99</span><p>Actually it costs $149.99</p>',
        'robots.txt': 'User-agent: *\nAllow: /'
    },
    
    # D-02: different products with different prices
    'd02_diff_products': {
        'index.html': '<h1>Basic</h1><span>$10</span><h1>Pro</h1><span>$50</span>',
        'robots.txt': 'User-agent: *\nAllow: /'
    },

    # D-02: monthly vs annual
    'd02_monthly_annual': {
        'index.html': '<h1>Subscription</h1><p>Price: $10/month or $100/year</p>',
        'robots.txt': 'User-agent: *\nAllow: /'
    },

    # D-02: different variants
    'd02_variants': {
        'index.html': '<h1>Shirt</h1><p>Red: $15</p><p>Blue: $20</p>',
        'robots.txt': 'User-agent: *\nAllow: /'
    },
    
    # E-01: genuine render-only fact
    'e01_render_only': {
        'index.html': '<script>document.write("<h1>Dynamic</h1><p>Company: Acme Corp</p>");</script>',
        'robots.txt': 'User-agent: *\nAllow: /'
    },
    
    # E-01: hydrated content already present
    'e01_hydrated_present': {
        'index.html': '<div id="app"><h1>Static</h1><p>Data</p></div><script>document.getElementById("app").innerHTML="<h1>Static</h1><p>Data</p>";</script>',
        'robots.txt': 'User-agent: *\nAllow: /'
    },
    
    # E-02: factual info in non-text
    'e02_factual_non_text': {
        'index.html': '<h1>Stats</h1><img src="chart.png">',
        'robots.txt': 'User-agent: *\nAllow: /'
    },
    
    # E-02: decorative image without alt
    'e02_decorative': {
        'index.html': '<h1>Welcome</h1><img src="spacer.gif" aria-hidden="true">',
        'robots.txt': 'User-agent: *\nAllow: /'
    },

    # G-02: true blocking modal
    'g02_true_modal': {
        'index.html': '<body><div id="modal" role="dialog" aria-modal="true"><h1>Subscribe</h1><a href="#">Close</a></div></body>',
        'robots.txt': 'User-agent: *\nAllow: /'
    },
    
    # G-02: non-blocking modal
    'g02_non_blocking': {
        'index.html': '<body><div id="modal" role="dialog"><h1>Subscribe</h1><a href="#">Close</a></div><main><a href="/link">Link</a></main></body>',
        'robots.txt': 'User-agent: *\nAllow: /'
    },
    
    # G-02: focus trap
    'g02_focus_trap': {
        'index.html': '<body><div id="trap"><a href="#1">1</a><a href="#2">2</a></div><script>document.getElementById("trap").addEventListener("keydown", e=>{if(e.key==="Tab") e.preventDefault();});</script></body>',
        'robots.txt': 'User-agent: *\nAllow: /'
    },
    
    # G-03: successful traditional nav
    'g03_trad_nav': {
        'index.html': '<nav><a href="/about.html">About</a></nav>',
        'about.html': '<h1>About</h1>',
        'robots.txt': 'User-agent: *\nAllow: /'
    },
    
    # G-03: successful SPA nav
    'g03_spa_nav': {
        'index.html': '<body><button onclick="document.body.innerHTML=\'<h1>About</h1>\'">About</button></body>',
        'robots.txt': 'User-agent: *\nAllow: /'
    },
    
    # G-03: nav to 404
    'g03_nav_404': {
        'index.html': '<nav><a href="/does-not-exist.html">Broken</a></nav>',
        'robots.txt': 'User-agent: *\nAllow: /'
    },
    
    # F-03: ambiguous entity
    'f03_ambiguous': {
        'index.html': '<title>Consulting</title><body><h1>We provide consulting</h1></body>',
        'robots.txt': 'User-agent: *\nAllow: /'
    },
    
    # F-03: clearly identified entity
    'f03_clear': {
        'index.html': '<html><head><title>Acme Corp Official</title></head><body><h1>Acme Corp</h1></body></html>',
        'robots.txt': 'User-agent: *\nAllow: /'
    },
    
    # Stale claim
    'stale_claim': {
        'index.html': '<h1>Copyright 2010</h1><p>Our upcoming product in 2011.</p>',
        'robots.txt': 'User-agent: *\nAllow: /'
    },
    
    # Clean site
    'clean_site': {
        'index.html': '<!DOCTYPE html><html><head><title>Clean Site</title></head><body><h1>Welcome to Clean Site</h1><p>We are a business.</p><nav><a href="/contact.html">Contact</a></nav></body></html>',
        'contact.html': '<!DOCTYPE html><html><head><title>Contact</title></head><body><h1>Contact Clean Site</h1></body></html>',
        'robots.txt': 'User-agent: *\nAllow: /'
    },
    
    # Deep architecture
    'deep_architecture': {
        'index.html': '<a href="/category/1/index.html">Cat 1</a>',
        'category/1/index.html': '<a href="/category/1/item/99/index.html">Item 99</a>',
        'category/1/item/99/index.html': '<h1>Item 99</h1><p>$45</p>',
        'robots.txt': 'User-agent: *\nAllow: /'
    }
}

for name, files in fixtures.items():
    path = os.path.join(base_dir, name)
    os.makedirs(path, exist_ok=True)
    for fname, content in files.items():
        fpath = os.path.join(path, fname)
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        with open(fpath, 'w') as f:
            f.write(content)

print(f'Generated {len(fixtures)} holdout fixtures.')
