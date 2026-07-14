import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Tableau de bord - Transition écologique", page_icon="🌱", layout="wide")

st.title("🌱 Tableau de bord - Transition écologique")

# =========================================================
# ÉTAPE 1 : choix du type de territoire (commune ou EPCI)
# =========================================================
type_territoire = st.radio(
    "Rechercher par :",
    ["Commune", "Communauté de communes / agglomération (EPCI)"],
    horizontal=True,
)

communes_selectionnees = []  # liste de dicts {nom, code, ...}
territoire_label = ""

if type_territoire == "Commune":
    nom_recherche = st.text_input("Nom de la commune", placeholder="ex : Lyon")

    if nom_recherche:
        with st.spinner("Recherche en cours..."):
            resp = requests.get(
                "https://geo.api.gouv.fr/communes",
                params={
                    "nom": nom_recherche,
                    "fields": "nom,code,codeDepartement,codeRegion,population,centre,surface,codeEpci",
                    "limit": 5,
                },
            )
        resultats = resp.json() if resp.status_code == 200 else []

        if not resultats:
            st.warning("Aucune commune trouvée avec ce nom.")
        else:
            noms_affiches = [f"{c['nom']} ({c['codeDepartement']})" for c in resultats]
            choix = st.selectbox("Sélectionnez la commune exacte", noms_affiches)
            commune = resultats[noms_affiches.index(choix)]
            communes_selectionnees = [commune]
            territoire_label = commune["nom"]

else:  # EPCI
    nom_epci = st.text_input(
        "Nom de la communauté de communes / agglomération",
        placeholder="ex : Grand Chalon",
    )

    if nom_epci:
        with st.spinner("Recherche en cours..."):
            resp = requests.get(
                "https://geo.api.gouv.fr/epcis",
                params={"nom": nom_epci, "fields": "nom,code,population", "boost": "population"},
            )
        epcis = resp.json() if resp.status_code == 200 else []

        if not epcis:
            st.warning("Aucun EPCI trouvé avec ce nom.")
        else:
            noms_affiches = [e["nom"] for e in epcis]
            choix = st.selectbox("Sélectionnez l'EPCI exact", noms_affiches)
            epci = epcis[noms_affiches.index(choix)]
            territoire_label = epci["nom"]

            with st.spinner("Récupération des communes membres..."):
                resp2 = requests.get(
                    f"https://geo.api.gouv.fr/epcis/{epci['code']}/communes",
                    params={"fields": "nom,code,codeDepartement,population,centre,surface"},
                )
            communes_selectionnees = resp2.json() if resp2.status_code == 200 else []
            st.caption(f"{len(communes_selectionnees)} communes membres")

# =========================================================
# ÉTAPE 2 : affichage des infos générales du territoire
# =========================================================
if communes_selectionnees:
    st.subheader(f"📍 {territoire_label}")

    population_totale = sum(c.get("population") or 0 for c in communes_selectionnees)
    surface_totale = sum(c.get("surface") or 0 for c in communes_selectionnees)

    col1, col2, col3 = st.columns(3)
    col1.metric("Population", f"{population_totale:,}".replace(",", " "))
    col2.metric("Nombre de communes", len(communes_selectionnees))
    col3.metric("Surface (ha)", f"{surface_totale:,.0f}".replace(",", " "))

    # Carte : un point par commune du territoire
    points = [
        {"lat": c["centre"]["coordinates"][1], "lon": c["centre"]["coordinates"][0]}
        for c in communes_selectionnees
        if "centre" in c
    ]
    if points:
        st.map(pd.DataFrame(points))

    # =========================================================
    # ÉTAPE 3 : indicateur ADEME - diagnostics de performance
    # énergétique (DPE) des logements
    # =========================================================
    st.divider()
    st.subheader("🏠 Performance énergétique des logements (ADEME)")

    if type_territoire == "Commune":
        commune = communes_selectionnees[0]
        with st.spinner("Interrogation de la base DPE de l'ADEME..."):
            try:
                resp_dpe = requests.get(
                    "https://data.ademe.fr/data-fair/api/v1/datasets/dpe-france/lines",
                    params={
                        "qs": f"Code_INSEE_(BAN):{commune['code']}",
                        "size": 1000,
                        "select": "Etiquette_DPE",
                    },
                    timeout=15,
                )
                data_dpe = resp_dpe.json()
                dpe_results = data_dpe.get("results", [])
            except Exception:
                dpe_results = None

        if dpe_results:
            df_dpe = pd.DataFrame(dpe_results)
            repartition = df_dpe["Etiquette_DPE"].value_counts().sort_index()
            st.bar_chart(repartition)
            st.caption(f"{len(dpe_results)} diagnostics trouvés pour {commune['nom']}")
        else:
            st.info(
                "Pas de résultat (ou champ de filtre à ajuster). Le nom exact des colonnes "
                "de ce jeu de données évolue parfois — vérifie-le sur la page "
                "[dpe-france](https://data.ademe.fr/datasets/dpe-france) avant de "
                "réutiliser cette requête."
            )
    else:
        st.caption(
            "Pour un EPCI, interroger l'ADEME nécessiterait de boucler sur chaque code "
            "commune (potentiellement lent). Étape suggérée pour plus tard : agréger les "
            "résultats commune par commune, ou filtrer directement par code département."
        )

    # =========================================================
    # ÉTAPE 4 : risques de vagues de chaleur (projections climat)
    # =========================================================
    st.divider()
    st.subheader("🌡️ Risque de vagues de chaleur (projections climatiques)")

    st.warning(
        "Il n'existe pas d'API publique gratuite donnant, en direct, une projection "
        "GIEC/vagues de chaleur **par commune**. Les données disponibles (ADEME/Météo-France, "
        "projet TRACC) sont publiées à l'échelle **régionale ou départementale**, sous forme "
        "de fichiers à télécharger — pas d'endpoint interrogeable en temps réel."
    )
    st.markdown(
        "Pour intégrer un vrai indicateur ici, l'approche réaliste est :\n"
        "1. Télécharger une fois les [données climatiques prospectives ADEME/Météo-France]"
        "(https://data.ademe.fr/datasets/donnees-climatiques-prospectives-france-2-7degc-vague-de-chaleur) "
        "(fichiers par département, scénarios +2°C / +2,7°C / +4°C)\n"
        "2. Les stocker dans un fichier local (`.csv`) du projet\n"
        "3. Faire correspondre le `codeDepartement` de la commune avec ce fichier pour "
        "afficher l'indicateur associé\n\n"
        "C'est un bon prochain exercice : ça demande de manipuler `pandas.read_csv()` "
        "et une jointure sur le code département — une étape clé pour progresser."
    )
