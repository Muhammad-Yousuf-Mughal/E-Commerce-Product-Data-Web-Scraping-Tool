# E-Commerce Product Data Web Scraper

<!-- Replace this with your website/project URL -->
https://e-commerce-data-web-scraping-tool.streamlit.app/

A professional, user-driven **Python web scraping** application that collects product data from e-commerce websites, cleans and validates it, then produces a **side-by-side comparison** with charts and downloadable CSV/Excel exports.

## Features

- **User-driven scraping** — paste product URLs *and/or* a category/search URL, then supply an optional keyword filter.
- **Adapter-based extractors** — site-specific parsers for Amazon, eBay, and Books to Scrape, plus a **generic extractor** that reads embedded `JSON-LD`, microdata, Open Graph tags and heuristics. Works on many real stores.
- **Automatic pagination** — follows "next" links to gather products from listings.
- **Polite scraping** — reads `robots.txt`, rate-limits per domain, rotates User-Agents, retries with backoff, and sets timeouts.
- **Robust error handling** — continues past individual bad products/pages; logs failures.
- **Data cleaning & validation** — deduplicates, normalises names, parses numeric prices, standardises ratings (0-5), and validates records.
- **Storage** — exports to **CSV** and **Excel**.
- **Analysis** — total products, average/min/max price, most common rating, available count, top-rated and cheapest products.
- **Visualisation** — price distribution, rating distribution, price-vs-rating, products-by-category charts.

## Tech Stack

- Python 3
- Requests + BeautifulSoup (lxml) — HTTP & parsing
- Pandas + OpenPyXL — data processing & Excel export
- Matplotlib — visualisations
- Streamlit — interactive web UI

## Project Structure

```
Data Web Scraper/
├── scraper/
│   ├── __init__.py          # public API exports
│   ├── logger.py            # rotating file + console logging
│   ├── http_client.py       # retries, UA rotation, rate limiting
│   ├── robots.py            # robots.txt compliance
│   ├── pagination.py        # follow next-page links
│   ├── pipeline.py          # end-to-end orchestration
│   ├── cleaner.py           # dedupe + name/price/rating normalisation
│   ├── validator.py         # record validation & summary
│   ├── storage.py           # CSV + Excel export
│   ├── analysis.py          # descriptive statistics
│   ├── visualization.py     # matplotlib charts
│   └── extractors/
│       ├── base.py          # Product dataclass + extractor ABC
│       ├── generic.py       # JSON-LD / microdata / meta extractor
│       ├── amazon.py        # Amazon selectors
│       ├── ebay.py          # eBay selectors
│       ├── books_to_scrape.py
│       └── registry.py      # domain -> extractor mapping
├── notebooks/
│   └── analysis.ipynb       # interactive demo
├── data/                    # raw scraped data (gitignored)
├── output/                  # CSV/Excel/charts (gitignored)
├── logs/                    # rotating logs (gitignored)
├── app.py                   # Streamlit UI
├── main.py                  # CLI runner
├── requirements.txt
└── .gitignore
```

## Installation

```bash
# Create and activate a virtual environment (recommended)
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Streamlit web app

```bash
streamlit run app.py
```

Open the local URL (usually `http://localhost:8501`), then:

1. Paste product URLs (one per line) **and/or** a category/search URL in the sidebar.
2. Optionally enter a product query to filter results by name.
3. Click **Scrape & Compare**.

The app shows a comparison table, key differences (cheapest, top rated, best value), summary metrics, charts, and CSV/Excel download buttons.

### CLI

```bash
# Scrape a single product page
python main.py --url "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"

# Scrape a category page (follows pagination) and filter by a keyword
python main.py --url "https://books.toscrape.com/catalogue/category/books/travel_2/index.html" --query travel --max-pages 3

# Scrape multiple product URLs to compare them
python main.py --url "https://example.com/product/123" "https://example.com/product/456" --output output --base-name comparison
```

### Notebook

Open `notebooks/analysis.ipynb` in Jupyter and run the cells to walk through the pipeline interactively.

## Notes on "realistic" scraping

Most real e-commerce sites apply anti-bot measures. The **generic extractor** reads structured `JSON-LD` data, which most product pages embed, so it works on many stores. Heavy anti-bot sites (e.g. Amazon) may serve CAPTCHAs to plain `requests`; for those you would add a dynamic browser engine (Playwright/Selenium) behind the `HttpClient`. This project keeps the default dependency set lightweight; a dynamic engine can be introduced as an optional extra.

Always respect each site's `robots.txt` and terms of service, and keep request rates low.

## Milestones (Beginner -> Professional)

1. Scrape one page
2. Scrape multiple pages via pagination
3. Clean & validate data
4. Export CSV + Excel
5. Exploratory data analysis
6. Visualisations
7. Logging, error handling, modular structure + interactive UI

## License

For educational use. Scrape responsibly.
