import os
import json

def run():
    base_dir = 'tests/generalization/holdout'
    os.makedirs(base_dir, exist_ok=True)
    
    fixtures = {
        'd01_unusual_robots': {'robots.txt': 'User-agent: OAI-SearchBot\nCrawl-delay: 10\nDisallow: /private\nDisallow: /'},
        'd02_same_entity': {
            'index.html': '<h1>Special Plan</h1><span itemprop="price">99.99</span><p>Actually it costs $149.99</p>',
            'robots.txt': 'User-agent: *\nAllow: /'
        },
        'd02_diff_products': {
            'index.html': '<h1>Basic</h1><span>$10</span><h1>Pro</h1><span>$50</span>',
            'robots.txt': 'User-agent: *\nAllow: /'
        },
        'd02_monthly_annual': {
            'index.html': '<h1>Subscription</h1><p>Price: $10/month or $100/year</p>',
            'robots.txt': 'User-agent: *\nAllow: /'
        },
        'd02_variants': {
            'index.html': '<h1>Shirt</h1><p>Red: $15</p><p>Blue: $20</p>',
            'robots.txt': 'User-agent: *\nAllow: /'
        },
        'e01_render_only': {
            'index.html': '<body></body><' + 'script>let d=document.createElement("div");d.innerHTML="<h1>Dynamic</h1><p>Company: Acme Corp</p>";document.body.appendChild(d);</' + 'script>',
            'robots.txt': 'User-agent: *\nAllow: /'
        },
        'e01_hydrated_present': {
            'index.html': '<div id="app"><h1>Static</h1><p>Data</p></div><' + 'script>let a=document.getElementById("app");if(a){a.innerHTML="<h1>Static</h1><p>Data</p>";}</' + 'script>',
            'robots.txt': 'User-agent: *\nAllow: /'
        },
        'e02_factual_non_text': {
            'index.html': '<h1>Stats</h1><img src="chart.png">',
            'robots.txt': 'User-agent: *\nAllow: /'
        },
        'e02_decorative': {
            'index.html': '<h1>Welcome</h1><img src="spacer.gif" aria-hidden="true">',
            'robots.txt': 'User-agent: *\nAllow: /'
        },
        'g02_true_modal': {
            'index.html': '<body><div id="modal" role="dialog" aria-modal="true"><h1>Subscribe</h1><a href="#">Close</a></div></body>',
            'robots.txt': 'User-agent: *\nAllow: /'
        },
        'g02_non_blocking': {
            'index.html': '<body><div id="modal" role="dialog"><h1>Subscribe</h1><a href="#">Close</a></div><main><a href="/link">Link</a></main></body>',
            'robots.txt': 'User-agent: *\nAllow: /'
        },
        'g02_focus_trap': {
            'index.html': '<body><div id="trap"><a href="#1">1</a><a href="#2">2</a></div><' + 'script>let t=document.getElementById("trap");if(t){t.addEventListener("keydown", function(e){if(e.key==="Tab") e.preventDefault();});}</' + 'script></body>',
            'robots.txt': 'User-agent: *\nAllow: /'
        },
        'g03_trad_nav': {
            'index.html': '<nav><a href="/about.html">About</a></nav>',
            'about.html': '<h1>About</h1>',
            'robots.txt': 'User-agent: *\nAllow: /'
        },
        'g03_spa_nav': {
            'index.html': '<body><button id="navbtn">About</button><' + 'script>document.getElementById("navbtn").addEventListener("click", function(){document.body.innerHTML="<h1>About</h1>";});</' + 'script></body>',
            'robots.txt': 'User-agent: *\nAllow: /'
        },
        'g03_nav_404': {
            'index.html': '<nav><a href="/does-not-exist.html">Broken</a></nav>',
            'robots.txt': 'User-agent: *\nAllow: /'
        },
        'f03_ambiguous': {
            'index.html': '<title>Consulting</title><body><h1>We provide consulting</h1></body>',
            'robots.txt': 'User-agent: *\nAllow: /'
        },
        'f03_clear': {
            'index.html': '<html><head><title>Acme Corp Official</title></head><body><h1>Acme Corp</h1></body></html>',
            'robots.txt': 'User-agent: *\nAllow: /'
        },
        'stale_claim': {
            'index.html': '<h1>Copyright 2010</h1><p>Our upcoming product in 2011.</p>',
            'robots.txt': 'User-agent: *\nAllow: /'
        },
        'clean_site': {
            'index.html': '<!DOCTYPE html><html><head><title>Clean Site</title></head><body><h1>Welcome to Clean Site</h1><p>We are a business.</p><nav><a href="/contact.html">Contact</a></nav></body></html>',
            'contact.html': '<!DOCTYPE html><html><head><title>Contact</title></head><body><h1>Contact Clean Site</h1></body></html>',
            'robots.txt': 'User-agent: *\nAllow: /'
        },
        'deep_architecture': {
            'index.html': '<a href="/category/1/index.html">Cat 1</a>',
            'category/1/index.html': '<a href="/category/1/item/99/index.html">Item 99</a>',
            'category/1/item/99/index.html': '<h1>Item 99</h1><p>$45</p>',
            'robots.txt': 'User-agent: *\nAllow: /'
        },
        'd01_sneaky_robots': {
            'robots.txt': 'User-agent: Googlebot\nDisallow: /private\n\nUser-agent: *\nDisallow: /'
        },
        'e01_js_price': {
            'index.html': '<body><div id="pricebox"></div></body><' + 'script>document.getElementById("pricebox").innerHTML="<h1>Product</h1><span itemprop=\'price\'>$99</span>";</' + 'script>',
            'robots.txt': 'User-agent: *\nAllow: /'
        },
        'g03_button_nav': {
            'index.html': '<button id="navbtn">About</button><' + 'script>document.getElementById("navbtn").addEventListener("click", function(){window.location.assign("/about.html");});</' + 'script>',
            'robots.txt': 'User-agent: *\nAllow: /'
        },
        'f03_misleading_schema': {
            'index.html': '<html><head><' + 'script type="application/ld+json">{"@type": "Organization", "name": "FakeCorp"}</' + 'script></head><body><h1>RealCorp</h1></body></html>',
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

    print(f"Generated {len(fixtures)} holdout fixtures.")

if __name__ == '__main__':
    run()
