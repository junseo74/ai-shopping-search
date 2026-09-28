# Data Source Access Notes

This document records only access paths that were checked against public official
documentation. APIs that require approval, account ownership, or unavailable
documentation are not implemented as working collectors.

## Connected in version 1

- `test_fixture`: Local test products only. These rows are stored with
  `data_source = "test_fixture"` so they are not confused with real collected
  merchant data.
- `ebay_browse`: Official eBay Browse API collector. It requires
  `EBAY_CLIENT_ID` and `EBAY_CLIENT_SECRET`. Without those credentials the
  collector fails explicitly and does not return synthetic products.
- `elevenst`: Official 11st Open API product search collector. It requires
  `ELEVENST_API_KEY`. Without that key the collector fails explicitly and does
  not return synthetic products.
- `approved_html`: HTML parser/collector for product listing pages where the
  operator has explicitly permitted automated collection and reuse. It requires
  `APPROVED_HTML_LIST_URLS` plus a selector config file referenced by
  `APPROVED_HTML_SELECTOR_CONFIG` or the default
  `backend/collectors/approved_html_selectors.yml`. Each listing URL is matched
  to an explicitly approved config entry and checked against robots.txt before
  fetching. No domestic marketplace is preconfigured because public pages or
  robots.txt allowance alone are not treated as permission.
- `shopping_auto`: Multi-source collector configured by
  `SHOPPING_SOURCES_CONFIG` or the default
  `backend/collectors/shopping_sources.yml`. Each source declares
  `collection_method` (`api` or `approved_html`), seller, listing URLs,
  selectors when needed, and `permission.approved`. Only approved sources are
  collected. Nike is kept as an HTML structure reference with
  `permission.approved = false`, so it is not automatically requested.
- `backend.tools.naver_shopping_html_analyzer`: Local-only analyzer for
  browser-saved Naver Shopping HTML files. It reports repeated product-card and
  field selector candidates, including how many cards each candidate matches,
  and can write a non-approved YAML draft with `selector_candidates`. It does
  not fetch Naver Shopping or mark any selector as confirmed. For saved ad
  product HTML where selectors have been manually verified, it can also extract
  the confirmed fields and write a local JSON file with
  `--extract-ad-products --output-json`. For a browser-saved full results page,
  it can parse product objects already embedded in `__NEXT_DATA__`, label rows
  whose titles match confirmed ad cards as `product_type = "ad"`, label the
  remaining rows as `product_type = "organic"`, remove duplicate product names,
  and write `{ "summary": ..., "products": [...] }` with
  `--extract-all-products --output-json`. The generated JSON is still a saved
  HTML artifact, not approval for live collection.
- `backend.tools.import_saved_naver_products`: Local-only importer for saved
  extraction JSON such as `naver_real_products.json`. It stores rows as
  `platform = "naver_shopping"` and `data_source = "saved_html_import"`, records
  the original saved search URL through `--source-url`, and skips rows whose
  product URL already exists so rerunning the import does not duplicate the same
  saved extraction.

Example saved JSON import:

```powershell
python -m backend.tools.import_saved_naver_products naver_real_products.json `
  --source-observed-at 2026-09-27T19:53:00+09:00
```

Example saved full-page extraction and import:

```powershell
python -m backend.tools.naver_shopping_html_analyzer naver_real.html `
  --extract-all-products `
  --output-json naver_all_products.json `
  --source-url "https://search.shopping.naver.com/search/all?query=YOUR_QUERY"

python -m backend.tools.import_saved_naver_products naver_all_products.json `
  --source-url "https://search.shopping.naver.com/search/all?query=YOUR_QUERY" `
  --source-observed-at 2026-09-27T19:53:00+09:00
```

Example local multi-file HTML merge:

```powershell
python -m backend.tools.merge_shopping_html naver_real.html saved_html_folder `
  --output-json merged_products.json
```

The merge tool reuses the saved-HTML analyzer, performs no network requests,
deduplicates primarily by product ID or normalized product URL, and writes the
same top-level JSON shape: `{ "summary": ..., "products": [...] }`.

Example approved/local automatic HTML collection:

```powershell
python -m backend.tools.auto_shopping_html `
  --config .\local_auto_html_sources.yml `
  --query "keyboard" `
  --max-pages 2 `
  --delay-seconds 1 `
  --timeout-seconds 10 `
  --output-json auto_collected_products.json
```

The auto HTML collector is for explicitly approved sources only. The config
must include `permission.approved: true`, a permission note or reference, a
`search_url_template` containing `{query}` and optionally `{page}`, and the CSS
selectors needed by `HtmlProductListParser`. It checks `robots.txt` before each
page request, does not bypass blocks, and reuses the same product URL
normalization/deduplication rules as the merge tool. No real marketplace source
is configured by default.

Local end-to-end test server:

```powershell
python -m backend.tools.local_test_shop_server --host 127.0.0.1 --port 8000
```

In a second PowerShell terminal:

```powershell
python -m backend.tools.auto_shopping_html `
  --config .\local_auto_html_sources.yml `
  --query "keyboard" `
  --max-pages 3 `
  --delay-seconds 0.2 `
  --timeout-seconds 5 `
  --output-json local_auto_products.json
```

Expected local result: 8 product cards across 3 pages, 2 duplicates removed by
normalized product URL, and 6 final unique products. This uses only
`localhost:8000`.

## Plausible official/API paths

- eBay Browse API: Official item search API for keyword/category/GTIN searches.
  It requires an application access token from the OAuth client credentials
  flow.
- Naver Shopping Search API: Naver Developers announced that Search Shopping,
  Book, and Document APIs were scheduled to end on 2026-07-31. As of
  2026-09-26 this project must treat Naver Shopping Search as unavailable
  unless Naver publishes a replacement product-search API.
- Kakao/Daum Search API: Kakao Developers documents REST API authentication,
  error handling, and quota behavior for Daum Search APIs. Current availability
  of a shopping-specific endpoint should be confirmed before implementation.
- YouTube Data API: Google documents YouTube Data API resources such as videos,
  playlists, and channels. Requests require an API key or OAuth 2.0 token.
  This is not the same as a public product-catalog search API for YouTube
  Shopping.
- Google Merchant API: Official product management API for products in a
  merchant's own Merchant Center account. It is not a general web-wide product
  search API.
- Coupang Open API: Official seller/integration API for product, order,
  promotion, and logistics management. It is primarily for approved sellers and
  integrators, not public marketplace-wide search.
- 11st Open API: Official Open API Center is online and documents
  `ProductSearch` for product search and `ProductInfo` for product information.
  The search response includes product name, price, image URL, seller, detail
  page URL, sale price, delivery information, review count, and benefits. An
  Open API key is required. The currently documented public fields do not expose
  a full text product detail description, so this collector leaves
  `detail_description` empty instead of scraping or guessing it.
- Gmarket / Auction: Current official documents found are seller/API management
  oriented. Auction documents developer ID, AppID, authentication ticket, SOAP
  services, and some partner-only APIs. Gmarket ESM Trading API documents seller
  product list/management APIs. Treat public marketplace-wide product search as
  unverified unless a current official public search API key path is confirmed.
- Danawa: An old Open API guide page is still discoverable, but current key
  issuance and permitted product search usage could not be confirmed from a
  current official access flow. Treat as unverified; do not scrape HTML.
- Danawa HTML pages: robots.txt currently allows major pages except specific
  paths, but Danawa customer/help pages also state that content use follows the
  terms/service guidance and that unauthorized reproduction/processing is not
  allowed. Robots allowance alone is not enough to treat product extraction as
  approved.
- Gmarket HTML pages: robots.txt contains a general disallow group for `*` and
  separate allowances for selected known bots/paths. Treat broad HTML product
  collection as not approved.
- 11st HTML pages: official Open API exists for product search. Prefer the API;
  do not scrape product detail pages unless a separate permission path is
  confirmed.

## Approval, partnership, or account permission required

- Instagram Shopping / Meta Commerce: Shopping tags require an approved business
  profile and a Meta product catalog. Product access depends on Graph API
  permissions, account ownership, and app review.
- YouTube Shopping: Shopping features depend on eligible channels, connected
  stores, and affiliate/merchant setup. It should be treated as an authorized
  integration, not an open product scraper.
- Karrot/Daangn: The public OpenAPI found is for ads campaign management, not
  secondhand item search. Product/item data requires a separate approved data
  partnership if available.
- Joonggonara: Public materials describe seller and service policies, but no
  official product-search API was confirmed. Treat as partnership-required.
- Bungaejangter: Public site lists business partnership contact information, but
  no public product-search API was confirmed. Treat as partnership-required.
- Instagram group buys: Do not automate collection from public posts without
  confirming Meta policy and account/API permissions.

## Public dataset import candidates

- Seoul Eco Mileage incentive product information: Seoul Open Data Plaza
  describes a dataset containing product name, price, description, and product
  image. The license is Korea Open Government License Type 1, attribution,
  commercial use and modification allowed. It does not clearly provide seller
  and per-product URL fields, so it is a partial product catalog source, not a
  complete shopping product source for this project.
- Public Procurement Service / Nara Marketplace delivery request item history:
  data.go.kr describes CSV data with item names, contract/delivery unit prices,
  supplier/company fields, and procurement dates. The license is unrestricted.
  These prices are procurement contract/delivery prices, not current retail
  sale prices. Do not display them as live shopping prices.
- Public Procurement Service facility material price data: official public
  data with material names and reference prices. It is useful as historical
  reference material pricing, but it has no seller/product URL and is not a
  retail shopping catalog.
- Commercial dataset vendors: Naver/Gmarket/Coupang-style product feeds are
  available from paid data vendors, but those require a purchase or data
  licensing agreement. Treat them as partnership/procurement candidates until a
  contract and license are available.

The project supports CSV/JSON imports through `/import/products`. Imported
products store `source_url`, `source_license`, and `source_observed_at` so older
dataset prices are not confused with current market prices.
