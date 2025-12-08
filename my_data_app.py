import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup as bs
from requests import get
import sqlite3
import os
import plotly.express as px
import base64

# ---------------------------------------------------
# Fonction pour mettre une image locale en fond
# ---------------------------------------------------
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

# ---------------------------------------------------
# Appliquer le fond
# ---------------------------------------------------
set_bg_image("image/img_file2.jpg")

# ---------------------------------------------------
# Contenu de la page
# ---------------------------------------------------
st.header("Évaluez mon application")
st.markdown("Merci de prendre un moment pour évaluer cette application :")

# ---------------------------------------------------
# CSS et design premium (ajout padding cellules)
# ---------------------------------------------------
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
.main .block-container {
    padding-top: 2.5rem;
    padding-left: 4rem;
    padding-right: 4rem;
}
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
div[role="slider"] > input[type="range"] {
    accent-color: #ef4444;
}
.stCheckbox > label {
    color: #F0F0F0;
}
a {
    color: #60a5fa !important;
    text-decoration: none;
}
/* Small cards look */
.metric-container {
    background-color: rgba(255,255,255,0.02);
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 8px;
}
/* Tableau : augmenter padding et taille */
.dataframe th, .dataframe td {
    padding: 12px 10px;
    font-size: 14px;
}
@media (max-width: 768px) {
    .main .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
    }
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# Header premium
# ---------------------------------------------------
st.markdown("<h1 class='title-style'>DAKAR AUTO SCRAPER</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle-style'>Analyse & Extraction Automatisée des Annonces Voitures / Motos</p>", unsafe_allow_html=True)

# ---------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------
st.sidebar.markdown("""
<h2 style='color:#1E90FF; text-align:center; margin-bottom:0.2rem;'> Navigation</h2>
<p style='color:#C8D6E5; text-align:center; margin-top:0.0rem; margin-bottom:0.6rem;'>Choisir une page</p>
<hr style='border:1px solid #1E90FF;'>
""", unsafe_allow_html=True)

page = st.sidebar.radio("Aller à :", ["Scraping", "Dashboard", "Ancien CSV", "À propos", "Évaluer l'application"])

# ---------------------------------------------------
# Fonction de scraping
# ---------------------------------------------------
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

# ---------------------------------------------------
# Nettoyage automatique
# ---------------------------------------------------
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
    df = df.drop_duplicates().reset_index(drop=True)
    return df

# ---------------------------------------------------
# Page Scraping
# ---------------------------------------------------
if page == "Scraping":
    st.header("Scraping Dakar Auto")
    num_pages = st.sidebar.number_input("Nombre de pages à scraper par catégorie", min_value=1, max_value=50, value=1, step=1)
    URLS = {
        "voitures": "https://dakar-auto.com/senegal/voitures-4?&page=",
        "location": "https://dakar-auto.com/senegal/location-de-voitures-19?&page=",
        "motos": "https://dakar-auto.com/senegal/motos-and-scooters-3?&page="
    }

    if st.button("Lancer le Scraping"):
        with st.spinner("Scraping en cours..."):
            for cat, base_url in URLS.items():
                df_tmp = scrape_dakar_auto(base_url, num_pages)
                df_tmp["category"] = cat
                df_tmp = clean_df(df_tmp)
                st.session_state[f"df_{cat}"] = df_tmp
        st.success("Scraping terminé !")

    for cat in URLS.keys():
        st.subheader(f"Données {cat.capitalize()}")
        c1, c2 = st.columns([1, 3])
        with c1:
            if st.button(f"Afficher {cat}"):
                if f"df_{cat}" in st.session_state:
                    st.dataframe(st.session_state[f"df_{cat}"], use_container_width=True, height=800)
                else:
                    st.warning(f"Aucune donnée disponible pour {cat}. Lancez le scraping d'abord.")
        with c2:
            if f"df_{cat}" in st.session_state:
                csv_bytes = st.session_state[f"df_{cat}"].to_csv(index=False).encode("utf-8")
                st.download_button(
                    label=f"Télécharger {cat}",
                    data=csv_bytes,
                    file_name=f"{cat}_scraped.csv",
                    mime="text/csv"
                )

    conn = sqlite3.connect("dakar_auto_data.db")
    for cat in URLS.keys():
        if f"df_{cat}" in st.session_state:
            st.session_state[f"df_{cat}"].to_sql(cat, conn, if_exists="replace", index=False)
    conn.close()
    st.info("Les données ont été sauvegardées dans la base SQLite 'dakar_auto_data.db'.")

# ---------------------------------------------------
# Page Dashboard
# ---------------------------------------------------
if page == "Dashboard":
    st.header("Dashboard complet")
    conn = sqlite3.connect("dakar_auto_data.db")
    dfs = {}
    for cat in ["voitures","location","motos"]:
        try:
            dfs[cat] = pd.read_sql(f"SELECT * FROM {cat}", conn)
            if not dfs[cat].empty:
                dfs[cat] = clean_df(dfs[cat])
        except Exception:
            dfs[cat] = pd.DataFrame()
    conn.close()

    if all(df.empty for df in dfs.values()):
        st.info("Aucune donnée disponible. Lancez d'abord le scraping.")
    else:
        df_total = pd.concat(dfs.values(), ignore_index=True)

        st.subheader("Informations sur le dataset")
        st.dataframe(df_total.isnull().sum(), height=400)
        st.markdown("**Statistiques descriptives :**")
        st.dataframe(df_total.describe(include='all').T, height=400)
        st.subheader("Données brutes")
        st.dataframe(df_total, height=800)

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

        csv = df_total.to_csv(index=False).encode("utf-8")
        st.download_button(label="Télécharger toutes les données du scraping", data=csv, file_name="dakar_auto_scraped_all.csv", mime="text/csv")

# ---------------------------------------------------
# Page Évaluer l'application (iframes plus grands)
# ---------------------------------------------------
if page == "Évaluer l'application":
    st.header("Évaluez mon application")
    st.markdown("Merci de prendre un moment pour évaluer cette application en utilisant les formulaires ci-dessous :")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """<iframe src="https://ee.kobotoolbox.org/x/2LOA6Lk0" width="100%" height="900" frameborder="0"></iframe>""",
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            """<iframe src="https://docs.google.com/forms/d/1T6ItdvCSsKZjP8R7oqvD3y9whWAxG_54oqHau_840ho/previewResponse" width="100%" height="900" frameborder="0"></iframe>""",
            unsafe_allow_html=True
        )

# ---------------------------------------------------
# Footer
# ---------------------------------------------------
st.markdown("""
<hr>
<p style='text-align:center; color:#C8D6E5; margin-top:20px;'>
Développé avec coeur pour la communauté Dakar Auto · Powered by Streamlit & BeautifulSoup
</p>
""", unsafe_allow_html=True)
