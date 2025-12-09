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
set_bg_image("image/img_file2.jpg")  # Chemin vers ton image

# ---------------------------------------------------
# 1. CSS et design premium (AJOUTS GW-STYLE)
# ---------------------------------------------------
# NOTE: je n'ai pas modifié le background global — les couleurs de fond restent celles de ton thème.
st.markdown("""
<style>
/* ----- Conserver ton style titre/subtitle mais améliorer l'espacement ----- */
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

/* ----- GW-like layout: plus de padding central ----- */
.main .block-container {
    padding-top: 2.5rem;
    padding-left: 4rem;
    padding-right: 4rem;
}

/* ----- Sidebar (améliorations visuelles sans changer le fond global) ----- */
.sidebar .sidebar-content {
    background-color: #14263F; /* conservation identique */
    color: #F0F0F0;
    padding-top: 1.25rem;
    padding-bottom: 1.25rem;
    border-radius: 8px;
}

/* Forcer couleur du texte dans la sidebar */
[data-testid="stSidebar"] * {
    color: #F0F0F0 !important;
}

/* ----- Boutons bleu électrique (conservés) ----- */
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

/* ----- Sliders et checkbox : GW-like but keep coherence ----- */
/* slider track accent */
div[role="slider"] > input[type="range"] {
    accent-color: #ef4444; /* rouge GW-like accent pour les sliders si présent */
}

/* Checkbox label color */
.stCheckbox > label {
    color: #F0F0F0;
}

/* Links */
a {
    color: #60a5fa !important;
    text-decoration: none;
}

/* Small cards look for metrics */
.metric-container {
    background-color: rgba(255,255,255,0.02);
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 8px;
}

/* Responsive adjustments */
@media (max-width: 768px) {
    .main .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
    }
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# 2. Header premium
# ---------------------------------------------------
st.markdown("<h1 class='title-style'>DAKAR AUTO SCRAPER</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle-style'>Analyse & Extraction Automatisée des Annonces Voitures / Motos</p>", unsafe_allow_html=True)

# ---------------------------------------------------
# 3. Sidebar navigation
# ---------------------------------------------------
st.sidebar.markdown("""
<h2 style='color:#1E90FF; text-align:center; margin-bottom:0.2rem;'>⚙️ Navigation</h2>
<p style='color:#C8D6E5; text-align:center; margin-top:0.0rem; margin-bottom:0.6rem;'>Choisir une page</p>
<hr style='border:1px solid #1E90FF;'>
""", unsafe_allow_html=True)

page = st.sidebar.radio("Aller à :", ["Scraping", "Dashboard", "Ancien CSV", "À propos", "Évaluer l'application"])

# ---------------------------------------------------
# 4. Fonction de scraping (identique à la tienne)
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
                # ne pas stopper l'exécution sur une annonce foireuse
                pass
    return pd.DataFrame(df_all)

# ---------------------------------------------------
# 5. Nettoyage automatique (remplacement None -> Unknown, numériques par défaut)
# ---------------------------------------------------
def clean_df(df):
    df = df.copy()
    # Colonnes texte
    str_cols = ["brand","model","fuel","gearbox","owner","adress","ref","category"]
    for col in str_cols:
        if col in df.columns:
            # remplacer None/NaN et nettoyer espaces
            df[col] = df[col].fillna("").astype(str).str.strip()
            df[col] = df[col].replace({"": "Unknown", "None": "Unknown", "nan": "Unknown"})
    # Colonnes numériques
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(-1).astype(int)
    if "km" in df.columns:
        # retirer tout sauf chiffres puis numeric
        df["km"] = df["km"].astype(str).str.replace(r"[^0-9]", "", regex=True)
        df["km"] = pd.to_numeric(df["km"], errors="coerce").fillna(0).astype(int)
    if "price" in df.columns:
        df["price"] = df["price"].astype(str).str.replace(r"[^0-9]", "", regex=True)
        df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0).astype(int)
    # Supprimer doublons
    df = df.drop_duplicates().reset_index(drop=True)
    return df

# ---------------------------------------------------
# 6. Page Scraping
# ---------------------------------------------------
if page == "Scraping":
    st.header("Scraping Dakar Auto")
    # on garde l'input dans la sidebar comme avant pour garder la mise en page GW-like
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
                df_tmp = clean_df(df_tmp)  # <-- Nettoyage automatique
                st.session_state[f"df_{cat}"] = df_tmp
        st.success("Scraping terminé !")

    # Affichage et téléchargement
    for cat in URLS.keys():
        st.subheader(f"Données {cat.capitalize()}")
        # Utiliser columns pour afficher boutons côte à côte
        c1, c2 = st.columns([1, 3])
        with c1:
            if st.button(f"Afficher {cat}"):
                if f"df_{cat}" in st.session_state:
                    st.dataframe(st.session_state[f"df_{cat}"], use_container_width=True)
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

    # Sauvegarde SQLite
    conn = sqlite3.connect("dakar_auto_data.db")
    for cat in URLS.keys():
        if f"df_{cat}" in st.session_state:
            st.session_state[f"df_{cat}"].to_sql(cat, conn, if_exists="replace", index=False)
    conn.close()
    st.info("Les données ont été sauvegardées dans la base SQLite 'dakar_auto_data.db'.")

# ---------------------------------------------------
# 7. Dashboard
# ---------------------------------------------------
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
        st.download_button(label="Télécharger toutes les données du scraping", data=csv, file_name="dakar_auto_scraped_all.csv", mime="text/csv")

# ---------------------------------------------------
# 8. Page anciens CSV
# ---------------------------------------------------
if page == "Ancien CSV":
    st.header("Fichiers CSV existants")
    data_folder = "data"
    if os.path.exists(data_folder):
        csv_files = [f for f in os.listdir(data_folder) if f.endswith(".csv")]
        if csv_files:
            for file in csv_files:
                if st.button(f"Afficher {file}"):
                    df_file = pd.read_csv(os.path.join(data_folder, file))
                    st.dataframe(df_file)
                csv_bytes = pd.read_csv(os.path.join(data_folder, file)).to_csv(index=False).encode("utf-8")
                st.download_button(label=f"Télécharger {file}", data=csv_bytes, file_name=file, mime="text/csv")
        else:
            st.warning("Aucun fichier CSV trouvé dans data.")
    else:
        st.info("Le dossier data n'existe pas.")

# ---------------------------------------------------
# 9. Page À propos
# ---------------------------------------------------
if page == "À propos":
    st.header("À propos de l'application")
    st.markdown("""
    Cette application est inspirée de **MyBestApp-2025**.
    Elle permet de scraper les annonces de Dakar Auto, visualiser les données,
    télécharger les CSV, et explorer les anciens fichiers existants.
    """)
    st.markdown("Créée par : *OGOUNCHI Géraud*")

# ---------------------------------------------------
# 10. Page Évaluer l'application
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
            """<iframe src="https://docs.google.com/forms/d/e/1FAIpQLScnFGbGlFams8BK3BgO7FofRdKPnDvQs7M4TTvatpr3Ybll4w/viewform?usp=header" width="100%" height="900" frameborder="0"></iframe>""",
            unsafe_allow_html=True
        )
# ---------------------------------------------------
# 11. Footer premium
# ---------------------------------------------------
st.markdown("""
<hr>
<p style='text-align:center; color:#C8D6E5; margin-top:20px;'>
Développé avec coeur pour la communauté Dakar Auto · Powered by Streamlit & BeautifulSoup
</p>
""", unsafe_allow_html=True)





