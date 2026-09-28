import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from html import escape
from urllib.parse import parse_qs, urlparse


PRODUCT_PAGES = {
    "1": [
        {
            "name": "Local Keyboard Alpha",
            "price": "49,900원",
            "shipping": "배송비 3,000원",
            "seller": "Local Mall",
            "url": "/products/100?utm_source=local",
            "image": "/images/100.jpg",
        },
        {
            "name": "Local Mouse Beta",
            "price": "29,900원",
            "shipping": "무료배송",
            "seller": "Second Mall",
            "url": "/products/200",
            "image": "/images/200.jpg",
        },
        {
            "name": "Local Laptop Stand Gamma",
            "price": "19,900원",
            "shipping": "배송비 2,500원",
            "seller": "Third Mall",
            "url": "/products/300",
            "image": "/images/300.jpg",
        },
    ],
    "2": [
        {
            "name": "Local Keyboard Alpha Updated Title",
            "price": "49,900원",
            "shipping": "배송비 3,000원",
            "seller": "Local Mall",
            "url": "/products/100?utm_campaign=again",
            "image": "/images/100.jpg",
        },
        {
            "name": "Local Monitor Delta",
            "price": "159,000원",
            "shipping": "배송비 5,000원",
            "seller": "Display Shop",
            "url": "/products/400?color=black&utm_medium=local",
            "image": "/images/400.jpg",
        },
        {
            "name": "Local Cable Epsilon",
            "price": "9,900원",
            "shipping": "무료배송",
            "seller": "Cable Store",
            "url": "/products/500",
            "image": "/images/500.jpg",
        },
    ],
    "3": [
        {
            "name": "Local Laptop Stand Gamma Duplicate",
            "price": "19,900원",
            "shipping": "배송비 2,500원",
            "seller": "Third Mall",
            "url": "/products/300?utm_source=page3",
            "image": "/images/300.jpg",
        },
        {
            "name": "Local Desk Mat Zeta",
            "price": "14,900원",
            "shipping": "배송비 2,500원",
            "seller": "Desk Goods",
            "url": "/products/600",
            "image": "/images/600.jpg",
        },
    ],
}


class LocalTestShopHandler(BaseHTTPRequestHandler):
    server_version = "LocalTestShop/0.1"

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/robots.txt":
            self._send_text("User-agent: *\nAllow: /search\n")
            return
        if parsed.path == "/search":
            params = parse_qs(parsed.query)
            query = params.get("q", [""])[0]
            page = params.get("page", ["1"])[0]
            self._send_html(render_search_page(query=query, page=page))
            return
        if parsed.path == "/":
            self._send_html(render_home_page())
            return
        self._send_text("not found", status=404)

    def log_message(self, format, *args):
        print("%s - - [%s] %s" % (self.address_string(), self.log_date_time_string(), format % args))

    def _send_html(self, body: str, status: int = 200):
        self._send(body, "text/html; charset=utf-8", status)

    def _send_text(self, body: str, status: int = 200):
        self._send(body, "text/plain; charset=utf-8", status)

    def _send(self, body: str, content_type: str, status: int):
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def render_home_page() -> str:
    return """
    <!doctype html>
    <html>
      <head><meta charset="utf-8"><title>Local Test Shop</title></head>
      <body>
        <h1>Local Test Shop</h1>
        <p>Try /search?q=keyboard&page=1</p>
      </body>
    </html>
    """


def render_search_page(query: str, page: str) -> str:
    products = PRODUCT_PAGES.get(page, [])
    cards = "\n".join(render_product_card(product) for product in products)
    return f"""
    <!doctype html>
    <html>
      <head><meta charset="utf-8"><title>Search {escape(query)} page {escape(page)}</title></head>
      <body>
        <main>
          <h1>Search results for {escape(query)}</h1>
          <section class="results" data-query="{escape(query)}" data-page="{escape(page)}">
            {cards}
          </section>
        </main>
      </body>
    </html>
    """


def render_product_card(product: dict[str, str]) -> str:
    return f"""
    <article class="product-card">
      <a class="product-link" href="{escape(product['url'])}">{escape(product['name'])}</a>
      <span class="price">{escape(product['price'])}</span>
      <span class="shipping">{escape(product['shipping'])}</span>
      <span class="seller">{escape(product['seller'])}</span>
      <img class="image" src="{escape(product['image'])}" alt="{escape(product['name'])}" />
    </article>
    """


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), LocalTestShopHandler)
    print(f"Local test shop running at http://{host}:{port}")
    print(f"Search URL example: http://{host}:{port}/search?q=keyboard&page=1")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping local test shop.")
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local test shopping search server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
