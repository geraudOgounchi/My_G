
# IMPORTS
import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup as bs
from requests import get
import sqlite3
import os
import plotly.express as px
import base64
import streamlit as st
import base64


# CONFIGURATION — BACKGROUND

def set_bg_image(image_file):
    with open(image_file, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpg;base64,{encoded}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

set_bg_image("image/img_file2.jpg")



# CSS — CUSTOM PREMIUM DESIGN
st.markdown("""
<style>
/* TITLES */
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

/* GENERAL LAYOUT */
.main .block-container {
    padding-top: 2.5rem;
    padding-left: 4rem;
    padding-right: 4rem;
}

/* SIDEBAR */
.sidebar .sidebar-content {
    background-color: #14263F;
    color: #F0F0F0;
    padding-top: 1.25rem;
    padding-bottom: 1.25rem;
    border-radius: 8px;
}
[data-testid="stSidebar"] * {
    color: #F0F0F0 !important;
}

/* BUTTONS */
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

/* OTHER */
.stCheckbox > label { color: #F0F0F0; }
a { color: #60a5fa !important; }

/* RESPONSIVE */
@media (max-width: 768px) {
    .main .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
    }
}
</style>
""", unsafe_allow_html=True)



# MAIN HEADER
st.markdown("<h1 class='title-style'>DAKAR AUTO SCRAPER</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle-style'>Automated Analysis & Extraction of Car / Motorcycle Listings</p>", unsafe_allow_html=True)


# SIDEBAR — NAVIGATION

st.sidebar.markdown("""
<h2 style='color:#1E90FF; text-align:center; margin-bottom:0.2rem;'> Navigation</h2>
<hr style='border:1px solid #1E90FF;'>
""", unsafe_allow_html=True)

page = st.sidebar.radio("Go to :", [
    "Scraping",
    "Dashboard",
    "Old CSV",
    "About",
    "Rate the App"
])



# FUNCTION: SCRAPING
def scrape_dakar_auto(url_base, num_pages):
    df_all = []
    for page_num in range(1, num_pages + 1):
        url = f"{url_base}{page_num}"
        try:
            res = get(url, timeout=15)
        except Exception:
            continue

        soup = bs(res.content, "html.parser")
        containers = soup.find_all("div", class_="listings-cards__list-item mb-md-3 mb-3")

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
                ref = attributes[0].text.split()[-1].strip() if len(attributes) > 0 else None
                km = attributes[1].text.replace("km","").strip() if len(attributes) > 1 else None
                gearbox = attributes[2].text.strip() if len(attributes) > 2 else None
                fuel = attributes[3].text.strip() if len(attributes) > 3 else None

                price_raw = cont.find("h3", "listing-card__header__price font-weight-bold text-uppercase mb-0")
                price = price_raw.text.strip().replace("FCFA","").replace(" ","") if price_raw else None

                owner_raw = cont.find("p", "time-author m-0")
                owner = owner_raw.a.text.replace("Par","").strip() if owner_raw and owner_raw.a else None

                addr_raw = cont.find("div", "col-12 entry-zone-address")
                adress = addr_raw.text.strip().replace("\n","") if addr_raw else None

                df_all.append({
                    "brand": brand,
                    "model": model,
                    "year": year,
                    "ref": ref,
                    "km": km,
                    "fuel": fuel,
                    "gearbox": gearbox,
                    "price": price,
                    "owner": owner,
                    "adress": adress
                })

            except Exception:
                pass

    return pd.DataFrame(df_all)


# FUNCTION: CLEANING
def clean_df(df):
    df = df.copy()

    str_cols = ["brand","model","fuel","gearbox","owner","adress","ref","category"]

    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()
            df[col] = df[col].replace({"": "Unknown", "None": "Unknown", "nan": "Unknown"})

    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(-1).astype(int)

    if "km" in df.columns:
        df["km"] = df["km"].astype(str).str.replace(r"[^0-9]", "", regex=True)
        df["km"] = pd.to_numeric(df["km"], errors="coerce").fillna(0).astype(int)

    if "price" in df.columns:
        df["price"] = df["price"].astype(str).str.replace(r"[^0-9]", "", regex=True)
        df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0).astype(int)

    return df.drop_duplicates().reset_index(drop=True)


# PAGE: SCRAPING
if page == "Scraping":

    st.header("Scraping Dakar Auto")

    num_pages = st.sidebar.number_input(
        "Number of pages to scrape per category",
        min_value=1, max_value=50, value=1, step=1
    )

    URLS = {
        "cars": "https://dakar-auto.com/senegal/voitures-4?&page=",
        "rental": "https://dakar-auto.com/senegal/location-de-voitures-19?&page=",
        "motorcycles": "https://dakar-auto.com/senegal/motos-and-scooters-3?&page="
    }

    if st.button("Start Scraping"):
        with st.spinner("Scraping in progress..."):
            for cat, base_url in URLS.items():
                df_tmp = scrape_dakar_auto(base_url, num_pages)
                df_tmp["category"] = cat
                df_tmp = clean_df(df_tmp)
                st.session_state[f"df_{cat}"] = df_tmp
        st.success("Scraping finished!")

    for cat in URLS.keys():
        st.subheader(f"Data: {cat.capitalize()}")

        c1, c2 = st.columns([1, 3])

        with c1:
            if st.button(f"Show {cat}"):
                if f"df_{cat}" in st.session_state:
                    st.dataframe(st.session_state[f"df_{cat}"], use_container_width=True)
                else:
                    st.warning("No data available.")

        with c2:
            if f"df_{cat}" in st.session_state:
                csv_bytes = st.session_state[f"df_{cat}"].to_csv(index=False).encode("utf-8")
                st.download_button(
                    label=f"Download {cat}",
                    data=csv_bytes,
                    file_name=f"{cat}_scraped.csv",
                    mime="text/csv"
                )

    conn = sqlite3.connect("dakar_auto_data.db")
    for cat in URLS.keys():
        if f"df_{cat}" in st.session_state:
            st.session_state[f"df_{cat}"].to_sql(cat, conn, if_exists="replace", index=False)
    conn.close()

    st.info("Data saved to dakar_auto_data.db.")


# PAGE: DASHBOARD
if page == "Dashboard":
    st.header("Dashboard complet")
    conn = sqlite3.connect("dakar_auto_data.db")
    dfs = {}
    for cat in ["voitures","location","motos"]:
        try:
            dfs[cat] = pd.read_sql(f"SELECT * FROM {cat}", conn)
            if not dfs[cat].empty:
                dfs[cat] = clean_df(dfs[cat])  # nettoyage au chargement
        except Exception:
            dfs[cat] = pd.DataFrame()
    conn.close()

    if all(df.empty for df in dfs.values()):
        st.info("Aucune donnée disponible. Lancez d'abord le scraping.")
    else:
        df_total = pd.concat(dfs.values(), ignore_index=True)

        st.subheader("Informations sur le dataset")
        st.markdown(f"- Dimensions : {df_total.shape[0]} lignes, {df_total.shape[1]} colonnes")
        st.markdown("**Valeurs manquantes par colonne :**")
        st.dataframe(df_total.isnull().sum())
        st.markdown("**Statistiques descriptives :**")
        st.dataframe(df_total.describe(include='all').T)
        st.subheader("Données brutes")
        st.dataframe(df_total)

        # Visualisations interactives
        if "price" in df_total.columns and df_total["price"].notnull().any():
            st.plotly_chart(px.histogram(df_total, x="price", nbins=30, title="Distribution des prix"), use_container_width=True)

        if "category" in df_total.columns:
            df_cat_count = df_total["category"].value_counts().reset_index()
            df_cat_count.columns = ["category","category_count"]
            st.plotly_chart(px.bar(df_cat_count, x="category", y="category_count", title="Nombre de listings par catégorie"), use_container_width=True)
            st.plotly_chart(px.pie(df_cat_count, names="category", values="category_count", title="Proportion par catégorie"), use_container_width=True)

        if "brand" in df_total.columns:
            df_brand_count = df_total["brand"].value_counts().reset_index()
            df_brand_count.columns = ["brand","count"]
            st.plotly_chart(px.bar(df_brand_count, x="brand", y="count", title="Nombre de véhicules par marque"), use_container_width=True)

            df_top10_brand = df_brand_count.head(10)
            st.plotly_chart(px.pie(df_top10_brand, names="brand", values="count", title="Top 10 marques"), use_container_width=True)

            if "price" in df_total.columns:
                df_brand_price = df_total.groupby("brand")["price"].mean().reset_index().sort_values("price", ascending=False)
                st.plotly_chart(px.bar(df_brand_price, x="brand", y="price", title="Prix moyen par marque"), use_container_width=True)

                st.plotly_chart(px.box(df_total, x="category", y="price", title="Boxplot : Prix par catégorie"), use_container_width=True)
                top10_brands = df_total["brand"].value_counts().head(10).index
                st.plotly_chart(px.box(df_total[df_total["brand"].isin(top10_brands)], x="brand", y="price", title="Boxplot : Prix par marque (Top 10)"), use_container_width=True)

        # Scatter price vs km
        if "price" in df_total.columns and "km" in df_total.columns:
            df_scatter = df_total[(df_total["price"].notnull()) & (df_total["km"].notnull())]
            if not df_scatter.empty:
                df_scatter["km"] = pd.to_numeric(df_scatter["km"], errors='coerce')
                df_scatter = df_scatter.dropna(subset=["km"])
                st.plotly_chart(px.scatter(df_scatter, x="km", y="price", color="category",
                                           hover_data=["brand","model","year"], title="Prix vs kilométrage"), use_container_width=True)

        if "year" in df_total.columns:
            df_year = df_total[df_total["year"].notnull()]
            st.plotly_chart(px.histogram(df_year, x="year", nbins=20, title="Répartition des années des véhicules"), use_container_width=True)

        csv = df_total.to_csv(index=False).encode("utf-8")
        st.download_button(label="Download all data", data=csv, file_name="dakar_auto_scraped_all.csv", mime="text/csv")



# PAGE: OLD CSV
if page == "Old CSV":

    st.header("Existing CSV Files")

    data_folder = "data"

    if os.path.exists(data_folder):
        csv_files = [f for f in os.listdir(data_folder) if f.endswith(".csv")]

        if csv_files:
            for file in csv_files:
                if st.button(f"Show {file}"):
                    df_file = pd.read_csv(os.path.join(data_folder, file))
                    st.dataframe(df_file)

                csv_bytes = pd.read_csv(os.path.join(data_folder, file)).to_csv(index=False).encode("utf-8")

                st.download_button(
                    label=f"Download {file}",
                    data=csv_bytes,
                    file_name=file,
                    mime="text/csv"
                )
        else:
            st.warning("No CSV files found.")
    else:
        st.info("The 'data' folder does not exist.")


# PAGE: ABOUT
if page == "About":

    st.header("About the App")

    st.markdown("""
    App inspired by **MyBestApp-2025**.
    Scraping, data exploration, dashboard, CSV download.
    Developed by **OGOUNCHI Géraud**.
    """)


# PAGE: RATE THE APP
if page == "Rate the App":

    st.header("Rate My App")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """<iframe src="https://ee.kobotoolbox.org/x/2LOA6Lk0" width="100%" height="900" frameborder="0"></iframe>""",
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            """<iframe src="https://docs.google.com/forms/d/e/1FAIpQLScnFGbGlFams8BK3BgO7FofRdKPnDvQs7M4TTvatpr3Ybll4w/viewform?usp=header" width="100%" height="900" frameborder="0"></iframe>""",
            unsafe_allow_html=True
        )


#  FOOTER
st.markdown("""
<hr>
<p style='text-align:center; color:#C8D6E5; margin-top:20px;'>
Developed for the Dakar Auto community · Powered by Streamlit & BeautifulSoup
</p>
""", unsafe_allow_html=True)


