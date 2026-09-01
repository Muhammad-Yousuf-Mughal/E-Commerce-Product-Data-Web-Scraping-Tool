"""Streamlit web app for the E-Commerce Compare Scraper."""

from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from scraper.logger import setup_logging
from scraper.pipeline import scrape_products
from scraper.storage import products_to_dataframe
from scraper.visualization import (
    plot_price_distribution,
    plot_price_vs_rating,
    plot_products_by_category,
    plot_rating_distribution,
)

setup_logging()

st.set_page_config(page_title="E-Commerce Compare Scraper", layout="wide")


# --------------------------------------------------------------------------- #
# Demo URL presets
# --------------------------------------------------------------------------- #
DEMO_URLS: dict[str, list[str]] = {
    "Gaming Laptops (Amazon)": [
        "https://www.amazon.com/Katana-15-6-165Hz-Gaming-Laptop/dp/B0DZFVBQLK",
        "https://www.amazon.com/ASUS-ROG-Strix-Gaming-Laptop/dp/B0DZZWMB2L",
        "https://www.amazon.com/dp/B0HF7SXJT8",
        "https://www.amazon.com/dp/B0DW238TXK",
        "https://www.amazon.com/dp/B0FSGJZDNT",
    ],
}


# --------------------------------------------------------------------------- #
# Session state
# --------------------------------------------------------------------------- #
if "df" not in st.session_state:
    st.session_state.df = None
if "stats" not in st.session_state:
    st.session_state.stats = {}
if "failures" not in st.session_state:
    st.session_state.failures = []
if "last_urls" not in st.session_state:
    st.session_state.last_urls = ""
if "product_links" not in st.session_state:
    st.session_state.product_links = ""
if "listing_url" not in st.session_state:
    st.session_state.listing_url = ""


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _parse_urls(raw: str) -> list[str]:
    return [line.strip() for line in raw.splitlines() if line.strip()]


def _excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Products")
    buffer.seek(0)
    return buffer.getvalue()


def _urls_look_complete(urls: list[str]) -> bool:
    for u in urls:
        u = u.strip()
        if not u:
            continue
        if not u.startswith(("http://", "https://")):
            return False
        domain_part = u.split("//", 1)[1].split("/")[0]
        if "." not in domain_part:
            return False
    return True


def _compare_summary(df: pd.DataFrame) -> dict:
    summary: dict = {}
    price_col = pd.to_numeric(df.get("price"), errors="coerce")
    rating_col = pd.to_numeric(df.get("rating"), errors="coerce")

    if price_col.notna().any():
        summary["cheapest"] = df.loc[price_col.idxmin()]
        summary["most_expensive"] = df.loc[price_col.idxmax()]

    if rating_col.notna().any():
        summary["top_rated"] = df.loc[rating_col.idxmax()]

    if price_col.notna().any() and rating_col.notna().any():
        value_df = pd.DataFrame({"price": price_col, "rating": rating_col}).dropna()
        if not value_df.empty:
            value_df["value"] = value_df["rating"] / value_df["price"]
            summary["best_value"] = df.loc[value_df["value"].idxmax()]

    if "available" in df.columns:
        summary["available_count"] = int(
            pd.to_numeric(df["available"], errors="coerce").fillna(0).sum()
        )

    return summary


def _render_summary(stats: dict) -> None:
    cols = st.columns(6)
    metrics = [
        ("Total products", stats.get("total_products")),
        ("Avg price", stats.get("avg_price")),
        ("Min price", stats.get("min_price")),
        ("Max price", stats.get("max_price")),
        ("Most common rating", stats.get("most_common_rating")),
        ("Available", stats.get("available_count")),
    ]
    for col, (label, value) in zip(cols, metrics):
        col.metric(label, value if value is not None else "—")


def _render_table(df: pd.DataFrame) -> None:
    display_cols = [
        c
        for c in ["name", "price", "rating", "rating_count", "available", "category", "source_site", "url"]
        if c in df.columns
    ]
    st.dataframe(df[display_cols], use_container_width=True, hide_index=True)


def _render_charts(df: pd.DataFrame) -> None:
    charts = [
        ("Price Distribution", plot_price_distribution(df)),
        ("Rating Distribution", plot_rating_distribution(df)),
        ("Price vs Rating", plot_price_vs_rating(df)),
        ("Products by Category", plot_products_by_category(df)),
    ]
    for i in range(0, len(charts), 2):
        cols = st.columns(2)
        for j in range(2):
            idx = i + j
            if idx < len(charts):
                title, fig = charts[idx]
                with cols[j]:
                    st.subheader(title)
                    st.pyplot(fig, use_container_width=True)


# --------------------------------------------------------------------------- #
# Header + demo
# --------------------------------------------------------------------------- #
st.title("E-Commerce Product Compare Scraper")
st.markdown(
    "Paste product links or a category/search URL below, then press **Scrape & Compare**."
)

col_left, col_center, col_right = st.columns([1, 3, 1])
with col_center:
    demo_choice = st.selectbox(
        "Load demo URLs",
        options=["None"] + list(DEMO_URLS.keys()),
        index=0,
    )
    if st.button("Load Demo URLs", use_container_width=True):
        if demo_choice != "None":
            st.session_state.product_links = "\n".join(DEMO_URLS[demo_choice])
            st.rerun()

st.markdown(
    "<small>**Note:** Amazon uses aggressive anti-bot measures. Some product pages "
    "may return bot-detection pages instead of the product HTML, causing those URLs "
    "to fail (they will be shown in red below). For reliable scraping of protected "
    "sites, a browser-based HTTP client (Playwright/Selenium) is recommended.</small>",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- #
# Inputs (centered, no sidebar)
# --------------------------------------------------------------------------- #
col_left, col_center, col_right = st.columns([1, 3, 1])
with col_center:
    product_links = st.text_area(
        "Product URLs (one per line)",
        key="product_links",
        placeholder="https://shop.example.com/product/123\nhttps://shop.example.com/product/456",
        height=150,
    )
    listing_url = st.text_input(
        "Or a category / search URL",
        key="listing_url",
        placeholder="https://books.toscrape.com/catalogue/category/books/travel_2/index.html",
    )
    product_query = st.text_input("Product query (optional filter)", placeholder="e.g. 'phone', 'travel'")
    c1, c2 = st.columns(2)
    with c1:
        max_pages = st.number_input("Max pages per listing", min_value=1, max_value=20, value=5, step=1)
        max_products = st.number_input("Max products to scrape", min_value=1, max_value=200, value=5, step=1)
    with c2:
        min_delay = st.slider("Delay between requests (s)", min_value=0.0, max_value=5.0, value=1.0, step=0.1)
    run_button = st.button("Scrape & Compare", type="primary", use_container_width=True)

all_urls = _parse_urls(product_links)
if listing_url:
    all_urls.append(listing_url.strip())

urls_key = "\n".join(all_urls)

# --------------------------------------------------------------------------- #
# Auto-scrape when URLs are pasted/changed (debounced by completeness check)
# --------------------------------------------------------------------------- #
should_auto_scrape = bool(all_urls) and _urls_look_complete(all_urls) and urls_key != st.session_state.last_urls

if should_auto_scrape or (run_button and all_urls):
    st.session_state.last_urls = urls_key
    with st.spinner("Scraping products… this can take a moment"):
        result = scrape_products(
            urls=all_urls,
            product_query=product_query,
            max_pages=int(max_pages),
            max_products=int(max_products),
            min_delay=float(min_delay),
            do_save=True,
            do_analyze=True,
            do_visualize=False,
        )

    products = result.get("products", [])
    failures = result.get("failures", [])
    st.session_state.failures = failures

    if products:
        st.session_state.df = products_to_dataframe(products)
        st.session_state.stats = result.get("stats", {})
    else:
        st.session_state.df = None
        st.session_state.stats = {}

# --------------------------------------------------------------------------- #
# Display results
# --------------------------------------------------------------------------- #
if st.session_state.df is not None and not st.session_state.df.empty:
    df = st.session_state.df
    stats = st.session_state.stats
    failures = st.session_state.failures

    st.success(f"Scraped **{len(df)}** products.")
    if failures:
        st.info(f"{len(failures)} URL(s) failed to scrape (see logs).")

    st.subheader("Summary")
    _render_summary(stats)

    st.subheader("Comparison Table")
    _render_table(df)

    st.subheader("Key Differences")
    summary = _compare_summary(df)
    col1, col2, col3 = st.columns(3)
    if "cheapest" in summary:
        with col1:
            st.markdown("**Cheapest**")
            st.write(f"{summary['cheapest']['name']}")
            st.caption(f"Price: {summary['cheapest'].get('price')} {summary['cheapest'].get('currency') or ''}")
    if "top_rated" in summary:
        with col2:
            st.markdown("**Top rated**")
            st.write(f"{summary['top_rated']['name']}")
            st.caption(f"Rating: {summary['top_rated'].get('rating')}")
    if "best_value" in summary:
        with col3:
            st.markdown("**Best value**")
            st.write(f"{summary['best_value']['name']}")
            st.caption(f"Price: {summary['best_value'].get('price')}")

    st.subheader("Visuals")
    _render_charts(df)

    st.subheader("Download")
    st.download_button(
        "Download CSV",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name="scraped_products.csv",
        mime="text/csv",
    )
    st.download_button(
        "Download Excel",
        data=_excel_bytes(df),
        file_name="scraped_products.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

elif st.session_state.failures:
    for f in st.session_state.failures:
        st.error(f"Failed to scrape **{f['url']}**: {f['error']}")
    st.warning(
        "All URLs failed to scrape. This often happens with Amazon/eBay due to anti-bot "
        "protection. For those sites, a browser-based HTTP client (Playwright/Selenium) "
        "is required. Try the *Books to Scrape* demo instead."
    )

elif run_button and not all_urls:
    st.info("Enter product URLs or a listing URL above, then click **Scrape & Compare**.")

else:
    st.info("Enter product URLs or a listing URL above to get started.")
