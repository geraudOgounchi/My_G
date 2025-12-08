import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup as bs
from requests import Session, get
import sqlite3
import os
import plotly.express as px
import base64
import time
import random
from requests.adapters import HTTPAdapter, Retry

# ---------------------------------------------------
# Keep your visual style (DO NOT change background)
# ---------------------------------------------------
st.set_page_config(layout="wide")
st.markdown("""
<style>
.title-style {
    text-align: center;
    font-size: 42px;
    color: #1E90FF;
    font-weight: 700;
    margin-top: -10px;
    text-shadow: 0 0 10px rgba(30,144,255,0.25);
}
.subtitle-style {
    text-align: center;
    font-size: 15px;
    color: #C8D6E5;
    margin-top: -6px;
}
.sidebar .sidebar-content {
    background-color: #14263F;
    color: #F0F0F0;
}
.stButton>button {
    background-color: #1E90FF;
    color: white;
    border-radius: 10px;
    padding: 0.6em 1.2em;
    font-size: 15px;
    border: none;
    box-shadow: 0 0 10px rgba(30,144,255,0.12);
    transition: 0.18s;
}
.stButton>button:hover {
    background-color: #63B3FF;
    transform: translateY(-1px);
}
.main .block-container {
    padding-top: 2.5rem;
    padding-left: 3rem;
    padding-right: 3rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='title-style'>DAKAR AUTO SCRAPER — PRO</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle-style'>Deep-search, cleaning avancé, KPIs et dashboard interactif</p>", unsafe_allow_html=True)

# ---------------------------------------------------
# Sidebar: controls
# ---------------------------------------------------
st.sidebar.markdown("## ⚙️ Paramètres")
mode = st.sidebar.selectbox("Mode de scraping", ["Standard (pages fixes)", "Deep Search (crawl)"])
num_pages = st.sidebar.number_input("Pages (si Standard)", min_value=1, max_value=200, value=2, step=1)
max_pages_deep = st.sidebar.number_input("Max pages (Deep)", min_value=10, max_value=1000, value=200, step=10)
rate_seconds = st.sidebar.slider("Pause entre requêtes (s)", 0.5, 5.0, 1.2, step=0.1)
user_agent = st.sidebar.text_input("User-Agent", value="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0")
deep_start_url = st.sidebar.text_input("Start URL (Deep)", value="https://dakar-auto.com/senegal/voitures-4?&page=1")

st.sidebar.markdown("---")
do_clean = st.sidebar.checkbox("Appliquer nettoyage avancé (recommandé)", True)
save_sql = st.sidebar.checkbox("Sauvegarder dans SQLite", True)
st.sidebar.markdown("---")

launch = st.sidebar.button("🚀 Lancer le scraping PRO")

# ---------------------------------------------------
# Helper: requests Session with retries
# ---------------------------------------------------
def make_session(user_agent_str):
    s = Session()
    retries = Retry(total=3, backoff_factor=0.8, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.headers.update({"User-Agent": user_agent_str})
    return s

# ---------------------------------------------------
# Robust scraping with optional deep crawling
# ---------------------------------------------------
def parse_listings_from_page(html):
    soup = bs(html, "html.parser")
    containers = soup.find_all("div", class_="listings-cards__list-item mb-md-3 mb-3")
    rows = []
    for cont in containers:
        try:
            title = cont.find("h2", class_="listing-card__header__title mb-md-2 mb-0")
            if not title:
                continue
            parts = title.a.text.strip().split()
            brand = parts[0] if len(parts) > 0 else None
            year = parts[-1] if len(parts) > 1 else None
            model = " ".join(parts[1:-1]) if len(parts) > 2 else None
            attributes = cont.find_all("li", "listing-card__attribute list-inline-item")
            ref = attributes[0].text.split()[-1].strip() if len(attributes)>0 else None
            km = attributes[1].text.replace("km","").strip() if len(attributes)>1 else None
            gearbox = attributes[2].text.strip() if len(attributes)>2 else None
            fuel = attributes[3].text.strip() if len(attributes)>3 else None
            price_raw = cont.find("h3", "listing-card__header__price font-weight-bold text-uppercase mb-0")
            price = price_raw.text.strip().replace("FCFA","").replace(" ","") if price_raw else None
            owner_raw = cont.find("p", "time-author m-0")
            owner = owner_raw.a.text.replace("Par","").strip() if owner_raw and owner_raw.a else None
            addr_raw = cont.find("div", "col-12 entry-zone-address")
            adress = addr_raw.text.strip().replace("\n","") if addr_raw else None
            rows.append({
                "brand": brand, "model": model, "year": year, "ref": ref,
                "km": km, "fuel": fuel, "gearbox": gearbox,
                "price": price, "owner": owner, "adress": adress
            })
        except Exception:
            continue
    return rows

# Try to detect last page from pagination links (best-effort)
def detect_last_page(html):
    soup = bs(html, "html.parser")
    pages = []
    for a in soup.select("ul.pagination li a, nav ul.pagination li a"):
        try:
            href = a.get("href", "")
            if "page=" in href:
                # parse last number
                import re
                m = re.search(r"page=(\d+)", href)
                if m:
                    pages.append(int(m.group(1)))
        except:
            pass
    return max(pages) if pages else None

# Caching scraping result for a combination of inputs
@st.cache_data(ttl=60*60)  # cache 1 hour
def do_scrape(mode, num_pages, max_pages_deep, start_url, ua, rate):
    session = make_session(ua)
    all_rows = []
    pages_scraped = 0

    if mode == "Standard (pages fixes)":
        # user supplies base urls for categories (we use your defaults)
        URLS = {
            "voitures": "https://dakar-auto.com/senegal/voitures-4?&page=",
            "location": "https://dakar-auto.com/senegal/location-de-voitures-19?&page=",
            "motos": "https://dakar-auto.com/senegal/motos-and-scooters-3?&page="
        }
        for cat, base_url in URLS.items():
            for p in range(1, num_pages+1):
                try:
                    r = session.get(f"{base_url}{p}", timeout=15)
                    if r.status_code != 200:
                        continue
                    rows = parse_listings_from_page(r.text)
                    for r_ in rows:
                        r_["category"] = cat
                    all_rows.extend(rows)
                    pages_scraped += 1
                    time.sleep(min(rate, 3) + random.uniform(0, .5))
                except Exception:
                    continue

    else:
        # Deep Search starting from start_url — crawl next pages by incrementing page param
        # best-effort: parse page param and increment until no results or max_pages reached
        import re
        m = re.search(r"(.*page=)(\d+)(.*)", start_url)
        if m:
            base = m.group(1)
            start_idx = int(m.group(2))
            tail = m.group(3) or ""
        else:
            # fallback: assume start_url ends with page=1 style
            base = start_url
            start_idx = 1
            tail = ""

        last_detected = None
        # Try to detect last page from first page
        try:
            r0 = session.get(start_url, timeout=15)
            last_detected = detect_last_page(r0.text)
        except Exception:
            last_detected = None

        # Plan pages to iterate
        if last_detected:
            pages_to_try = list(range(start_idx, min(last_detected+1, start_idx + max_pages_deep)))
        else:
            pages_to_try = list(range(start_idx, start_idx + max_pages_deep))

        for p in pages_to_try:
            cur_url = f"{base}{p}{tail}"
            try:
                r = session.get(cur_url, timeout=15)
                if r.status_code != 200:
                    # if many consecutive failures, break
                    continue
                rows = parse_listings_from_page(r.text)
                if not rows:
                    # no listings -> likely end of pages
                    break
                for r_ in rows:
                    r_["category"] = "deep"
                all_rows.extend(rows)
                pages_scraped += 1
                time.sleep(min(rate, 2.5) + random.uniform(0, .6))
            except Exception:
                # don't stop on occasional errors
                continue

    df = pd.DataFrame(all_rows)
    return df, pages_scraped, len(all_rows)

# ---------------------------------------------------
# Advanced cleaning (normalization + dedupe strategy)
# ---------------------------------------------------
def advanced_clean(df):
    if df is None or df.empty:
        return df
    df = df.copy()

    # Standardize string columns and replace missing with "Unknown"
    str_cols = ["brand","model","fuel","gearbox","owner","adress","ref","category"]
    for c in str_cols:
        if c in df.columns:
            df[c] = df[c].fillna("").astype(str).str.strip()
            df[c] = df[c].replace({"": "Unknown", "None": "Unknown", "nan": "Unknown"})

    # Normalize brand casing (capitalize)
    if "brand" in df.columns:
        df["brand"] = df["brand"].apply(lambda x: x.title() if isinstance(x, str) else x)

    # Clean numeric columns
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"].astype(str).str.replace(r"[^0-9\-]", "", regex=True), errors="coerce").fillna(-1).astype(int)
    if "km" in df.columns:
        df["km"] = pd.to_numeric(df["km"].astype(str).str.replace(r"[^0-9]", "", regex=True), errors="coerce").fillna(0).astype(int)
    if "price" in df.columns:
        df["price"] = pd.to_numeric(df["price"].astype(str).str.replace(r"[^0-9]", "", regex=True), errors="coerce").fillna(0).astype(int)

    # Remove exact duplicates
    df = df.drop_duplicates().reset_index(drop=True)

    # Smart dedupe: prefer rows with price>0 and km>0; group by (brand, model, ref) or (brand,model,year)
    key_cols = []
    if all(c in df.columns for c in ["brand","model","ref"]):
        key_cols = ["brand","model","ref"]
    elif all(c in df.columns for c in ["brand","model","year"]):
        key_cols = ["brand","model","year"]

    if key_cols:
        def choose_best(group):
            # prefer larger non-zero price and non-zero km
            group = group.copy()
            group["score"] = ((group.get("price", 0) > 0).astype(int) * 3) + ((group.get("km", 0) > 0).astype(int) * 1)
            best = group.sort_values(["score", "price", "km"], ascending=[False, False, False]).iloc[0]
            return best.drop(labels=["score"], errors="ignore")
        df = df.groupby(key_cols, dropna=False).apply(choose_best).reset_index(drop=True)

    return df

# ---------------------------------------------------
# When launch clicked: run scraping (cached)
# ---------------------------------------------------
if launch:
    with st.spinner("Lancement du scraping PRO..."):
        df_raw, pages_done, rows_count = do_scrape(mode, num_pages, max_pages_deep, deep_start_url, user_agent, rate_seconds)
    st.success(f"Scraping terminé — pages scrappées: {pages_done}, annonces trouvées: {rows_count}")

    if df_raw is None or df_raw.empty:
        st.warning("Aucune annonce récupérée — vérifier l'URL, user-agent ou paramètres.")
    else:
        # advanced cleaning optional
        if do_clean:
            df_clean = advanced_clean(df_raw)
        else:
            df_clean = df_raw.copy()

        # save to session and optionally sqlite
        st.session_state["df_all"] = df_clean
        if save_sql:
            conn = sqlite3.connect("dakar_auto_data.db")
            # store in a single table with category preserved
            df_clean.to_sql("dakar_auto_all", conn, if_exists="replace", index=False)
            conn.close()
            st.info("Données sauvegardées dans dakar_auto_data.db (table: dakar_auto_all)")

        # show a few KPIs
        total = len(df_clean)
        avg_price = int(df_clean["price"].mean()) if "price" in df_clean.columns and not df_clean["price"].isnull().all() else 0
        median_price = int(df_clean["price"].median()) if "price" in df_clean.columns and not df_clean["price"].isnull().all() else 0
        unique_brands = df_clean["brand"].nunique() if "brand" in df_clean.columns else 0

        k1, k2, k3, k4 = st.columns([1,1,1,1])
        k1.metric("Total annonces", f"{total:,}")
        k2.metric("Prix moyen (FCFA)", f"{avg_price:,}")
        k3.metric("Prix médian (FCFA)", f"{median_price:,}")
        k4.metric("Marques uniques", f"{unique_brands}")

        # quick preview
        st.subheader("Aperçu des données (nettoyées)")
        st.dataframe(df_clean.head(200), use_container_width=True)

        # Allow user to download full cleaned CSV
        csv_bytes = df_clean.to_csv(index=False).encode("utf-8")
        st.download_button("Télécharger dataset complet (cleaned).csv", csv_bytes, "dakar_auto_cleaned.csv", "text/csv")

# ---------------------------------------------------
# Dashboard: advanced filters & interactive exploration
# ---------------------------------------------------
st.markdown("---")
st.header("Dashboard interactif")

df_all = st.session_state.get("df_all", None)
# If not in session, try to load from sqlite (if exists)
if df_all is None:
    if os.path.exists("dakar_auto_data.db"):
        try:
            conn = sqlite3.connect("dakar_auto_data.db")
            df_tmp = pd.read_sql("SELECT * FROM dakar_auto_all", conn)
            conn.close()
            df_all = advanced_clean(df_tmp)
            st.session_state["df_all"] = df_all
            st.success("Chargé les données depuis la base SQLite.")
        except Exception:
            df_all = None

if df_all is None or df_all.empty:
    st.info("Aucune donnée disponible pour le Dashboard — lancez d'abord le scraping PRO.")
else:
    # Filters
    st.sidebar.markdown("### 🔎 Filtres Dashboard")
    brands = sorted(df_all["brand"].unique()) if "brand" in df_all.columns else []
    cats = sorted(df_all["category"].unique()) if "category" in df_all.columns else []
    min_price = int(df_all["price"].min()) if "price" in df_all.columns else 0
    max_price = int(df_all["price"].max()) if "price" in df_all.columns else 10000000
    min_year = int(df_all["year"].replace(-1, pd.NA).dropna().min()) if "year" in df_all.columns else 1900
    max_year = int(df_all["year"].max()) if "year" in df_all.columns else 2050

    sel_brand = st.sidebar.multiselect("Marques", options=brands, default=brands[:6])
    sel_cat = st.sidebar.multiselect("Catégories", options=cats, default=cats if cats else [])
    sel_price = st.sidebar.slider("Prix (FCFA)", min_price, max_price, (min_price, max_price))
    sel_year = st.sidebar.slider("Année", min_year if min_year>1900 else 1900, max_year, (min_year if min_year>1900 else 1900, max_year))
    text_search = st.sidebar.text_input("Recherche texte (brand/model/address/ref)")

    # apply filters
    df_view = df_all.copy()
    if sel_brand:
        df_view = df_view[df_view["brand"].isin(sel_brand)]
    if sel_cat:
        df_view = df_view[df_view["category"].isin(sel_cat)]
    if "price" in df_view.columns:
        df_view = df_view[(df_view["price"] >= sel_price[0]) & (df_view["price"] <= sel_price[1])]
    if "year" in df_view.columns:
        # treat -1 as unknown -> include if range includes -1? we'll exclude unknown by default
        df_view = df_view[(df_view["year"] >= sel_year[0]) & (df_view["year"] <= sel_year[1])]

    if text_search:
        s = text_search.strip().lower()
        mask = pd.Series(False, index=df_view.index)
        for c in ["brand","model","adress","ref"]:
            if c in df_view.columns:
                mask = mask | df_view[c].astype(str).str.lower().str.contains(s)
        df_view = df_view[mask]

    st.subheader(f"Résultats filtrés ({len(df_view):,} annonces)")

    # show small KPIs for filtered view
    c1, c2, c3 = st.columns(3)
    c1.metric("Annonces filtrées", f"{len(df_view):,}")
    if "price" in df_view.columns and not df_view["price"].empty:
        c2.metric("Prix moyen (filtré)", f"{int(df_view['price'].mean()):,}")
        c3.metric("Prix médian (filtré)", f"{int(df_view['price'].median()):,}")
    else:
        c2.metric("Prix moyen (filtré)", "0")
        c3.metric("Prix médian (filtré)", "0")

    # Main visualizations
    col1, col2 = st.columns(2)
    with col1:
        if "price" in df_view.columns and not df_view["price"].empty:
            fig = px.histogram(df_view, x="price", nbins=40, title="Distribution des prix")
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        if "brand" in df_view.columns:
            vc = df_view["brand"].value_counts().reset_index().rename(columns={"index":"brand","brand":"count"})
            fig2 = px.bar(vc.head(15), x="brand", y="count", title="Top marques (filtré)")
            st.plotly_chart(fig2, use_container_width=True)

    # Scatter price vs km
    if all(c in df_view.columns for c in ["price","km"]):
        df_sc = df_view[(df_view["price"]>0)]
        if not df_sc.empty:
            fig3 = px.scatter(df_sc, x="km", y="price", color="brand", hover_data=["model","year","adress"], title="Prix vs Kilométrage")
            st.plotly_chart(fig3, use_container_width=True)

    # Data table and export filtered
    st.subheader("Table des annonces (filtrées)")
    st.dataframe(df_view.reset_index(drop=True), use_container_width=True)
    csv_f = df_view.to_csv(index=False).encode("utf-8")
    st.download_button("Télécharger (filtré).csv", csv_f, "dakar_auto_filtered.csv", "text/csv")

# ---------------------------------------------------
# End: footer
# ---------------------------------------------------
st.markdown("---")
st.markdown("<p style='text-align:center; color:#C8D6E5;'>Développé avec ❤️ — Deep Search & Dashboard PRO · Streamlit & BeautifulSoup</p>", unsafe_allow_html=True)
