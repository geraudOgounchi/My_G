import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup as bs
from requests import get
import base64

# ---------------------------------------------------
# SCRAPER FUNCTION
# ---------------------------------------------------
def scrape_dakar_auto(url_base, start_page=1, end_page=2):
    df_all = []

    for page in range(start_page, end_page + 1):
        url = f"{url_base}{page}"
        res = get(url)
        soup = bs(res.content, "html.parser")

        containers = soup.find_all(
            'div',
            class_='listings-cards__list-item mb-md-3 mb-3'
        )

        for cont in containers:
            try:
                # Title => brand, model, year
                title = cont.find('h2', class_='listing-card__header__title mb-md-2 mb-0')
                if not title:
                    continue

                gen_info = title.a.text.strip().split()
                brand  = gen_info[0]
                year   = gen_info[-1]
                model  = " ".join(gen_info[1:-1])

                # Attributes: ref, km, fuel, gearbox
                attributes = cont.find_all('li', 'listing-card__attribute list-inline-item')
                ref     = attributes[0].text.split()[-1].strip() if len(attributes) > 0 else None
                km      = attributes[1].text.replace("km", "").strip() if len(attributes) > 1 else None
                fuel    = attributes[2].text.strip() if len(attributes) > 2 else None
                gearbox = attributes[3].text.strip() if len(attributes) > 3 else None

                # Price
                price_raw = cont.find(
                    'h3',
                    'listing-card__header__price font-weight-bold text-uppercase mb-0'
                )
                price = price_raw.text.strip().replace("FCFA","").replace(" ", "") if price_raw else None

                # Owner
                owner_raw = cont.find('p', 'time-author m-0')
                owner = owner_raw.a.text.replace("Par","").strip() if owner_raw and owner_raw.a else None

                # Address
                addr_raw = cont.find('div', 'col-12 entry-zone-address')
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
                    "adress": adress,
                    "page": page
                })

            except:
                pass

    return pd.DataFrame(df_all)



# ---------------------------------------------------
# STREAMLIT APP
# ---------------------------------------------------
st.markdown("<h1 style='text-align: center; color: black;'>SCRAPER DAKAR-AUTO</h1>", unsafe_allow_html=True)

st.markdown("""
Cette application permet de scraper les voitures, motos et locations depuis **Dakar-Auto** 🚗  
Vous pouvez choisir l’URL, la page de début et la page de fin.
""")

st.markdown("""
<style>
div.stButton {text-align:center}
.stButton>button {
    font-size: 14px;
    height: 3em;
    width: 25em;
}
</style>""", unsafe_allow_html=True)


# ---------------------------------------------------
# USER INPUTS
# ---------------------------------------------------
st.subheader("Paramètres du scraping")

url_base = st.text_input(
    "Base URL (ex: https://dakar-auto.com/senegal/voitures-)",
    "https://dakar-auto.com/senegal/voitures-"
)

start_page = st.number_input("Page de début", min_value=1, value=1)
end_page   = st.number_input("Page de fin", min_value=1, value=2)


# ---------------------------------------------------
# SCRAPE BUTTON
# ---------------------------------------------------
if st.button("Lancer le scraping"):
    st.info("Scraping en cours… patience…")
    df = scrape_dakar_auto(url_base, start_page, end_page)

    st.success(f"Scraping terminé ! {df.shape[0]} lignes récupérées.")
    st.dataframe(df)

    # --- Download CSV ---
    csv = df.to_csv(index=False).encode()
    st.download_button(
        label="Télécharger le CSV",
        data=csv,
        file_name="dakar_auto_data.csv",
        mime="text/csv"
    )

