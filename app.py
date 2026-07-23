import streamlit as st # bibliothèque pour créer l'interface web
import requests # bibliothèque pour appeler les API (geo.api.gouv.fr, ADEME)
import pandas as pd # bibliothèque pour manipuler les tableaux de données
import time #importation d'une bibliotheque utilisé pour connaitre le temps de chargement d'une page.
from datetime import datetime # idem
import numpy as np
import plotly.express as px  # pour le graphique en barres avec étiquettes de pourcentage

# Initialisation du temps de départ
st.session_state.start_time = time.time()
    
st.set_page_config(page_title="Tableau de bord - Transition écologique", page_icon="🌱", layout="wide") # configure l'onglet du navigateur et l'affichage large

st.title("🌱 Tableau de bord - Transition écologique")  # affiche le titre principal de la page


# =========================================================
# FONCTIONS
# =========================================================
# ---------------------------------------------------------
# Analyse des élus municipaux (répertoire national des élus)
# ---------------------------------------------------------
@st.cache_data # met en cache le résultat pour ne pas recharger les CSV à chaque interaction

# Charge les tableaux de données et créé un identifiant commun aux tableaux
def charger_donnees_elus():
    elus_epci = pd.read_csv("elus-conseillers-communautaires-epci.csv", sep=";", encoding="utf-8", dtype=str)
    elus_2026 = pd.read_csv("elus-conseillers-municipaux-cm.csv", sep=";", encoding="utf-8", dtype=str)
    elus_sortants = pd.read_csv("mun2026-cm-sortants-20260227.csv", sep=";", encoding="utf-8", dtype=str)

    elus_epci["id_unique"] = (
        elus_epci["Prénom de l'élu"].str.strip().str.upper() + "_" +
        elus_epci["Nom de l'élu"].str.strip().str.upper() + "_" +
        elus_epci["Libellé de la commune de rattachement"].str.strip().str.upper()
    )
    elus_2026["id_unique"] = (
        elus_2026["Prénom de l'élu"].str.strip().str.upper() + "_" +
        elus_2026["Nom de l'élu"].str.strip().str.upper() + "_" +
        elus_2026["Libellé de la commune"].str.strip().str.upper()
    )
    elus_sortants["id_unique"] = (
        elus_sortants["Prénom de l'élu"].str.strip().str.upper() + "_" +
        elus_sortants["Nom de l'élu"].str.strip().str.upper() + "_" +
        elus_sortants["Libellé de la commune"].str.strip().str.upper()
    )

    # sélectionne uniquement les colonnes utiles pour le tableau principal, copie le sous-tableau et renomme certaines colonnes
    elus_municipaux = elus_2026[
        ["Prénom de l'élu", "Nom de l'élu", "Libellé de la commune", "Code de la commune", "Libellé de la fonction", "id_unique"]
    ].copy().rename(columns={
        "Prénom de l'élu": "Prénom",
        "Nom de l'élu": "Nom",
        "Libellé de la fonction": "Poste à la commune",
    })
    # Rajoute deux colonnes avec des test pour savoir si l'élu était déjà élu au mandat précédent, et s'il est présent a la comcom
    elus_municipaux["Elu au mandat précédent"] = elus_municipaux["id_unique"].isin(elus_sortants["id_unique"])
    elus_municipaux["Elu à la communauté de communes"] = elus_municipaux["id_unique"].isin(elus_epci["id_unique"])

    epci_info = elus_epci[["id_unique", "Libellé de l'EPCI"]].drop_duplicates(subset="id_unique") # garde une seule ligne par élu avec le nom de son EPCI
    elus_municipaux = elus_municipaux.merge(epci_info, on="id_unique", how="left") # ajoute le nom de l'EPCI au tableau principal

    return elus_epci, elus_municipaux # renvoie les deux tableaux utiles pour la suite

def calculer_synthese(elus_municipaux, codes_communes): 
    data = elus_municipaux[elus_municipaux["Code de la commune"].isin(codes_communes)] # garde uniquement les élus des communes sélectionnées

    synthese = data.groupby(["Libellé de la commune", "Code de la commune"]).agg( # regroupe les élus par commune
        nb_elus=("id_unique", "count"), # compte le nombre total d'élus par commune
        nb_nouveaux=("Elu au mandat précédent", lambda x: (~x).sum()), # compte les élus absents du mandat précédent (donc nouveaux)
        nb_elus_epci=("Elu à la communauté de communes", "sum"), # compte les élus qui siègent aussi à l'EPCI
    ).reset_index() # transforme l'index de groupe en colonnes normales

    nouveaux_epci = data[data["Elu à la communauté de communes"] == True].groupby(
        ["Libellé de la commune", "Code de la commune"]
    ).agg(nb_nouveaux_epci=("Elu au mandat précédent", lambda x: (~x).sum())).reset_index()

    synthese = synthese.merge(nouveaux_epci, on=["Libellé de la commune", "Code de la commune"], how="left")
    synthese["nb_nouveaux_epci"] = synthese["nb_nouveaux_epci"].fillna(0).astype(int)

    synthese["pct_nouveaux"] = (synthese["nb_nouveaux"] / synthese["nb_elus"] * 100).round(0)
    synthese["pct_nouveaux_epci"] = (
        synthese["nb_nouveaux_epci"] / synthese["nb_elus_epci"] * 100
    ).round(0).fillna(0)

    # Création d'un ligne de total en fin de tableau
    total = {
        "Libellé de la commune": "TOTAL",
        "Code de la commune": "",
        "nb_elus": synthese["nb_elus"].sum(),
        "nb_nouveaux": synthese["nb_nouveaux"].sum(),
        "nb_elus_epci": synthese["nb_elus_epci"].sum(),
        "nb_nouveaux_epci": synthese["nb_nouveaux_epci"].sum(),
    }
    total["pct_nouveaux"] = round(total["nb_nouveaux"] / total["nb_elus"] * 100, 0) if total["nb_elus"] > 0 else 0
    total["pct_nouveaux_epci"] = round(total["nb_nouveaux_epci"] / total["nb_elus_epci"] * 100, 0) if total["nb_elus_epci"] > 0 else 0

    synthese = pd.concat([synthese, pd.DataFrame([total])], ignore_index=True)

    synthese = synthese[["Libellé de la commune", "nb_elus", "nb_nouveaux", "pct_nouveaux","nb_elus_epci", "nb_nouveaux_epci", "pct_nouveaux_epci"]]
    
    synthese.columns = pd.MultiIndex.from_tuples([
        ("", "Libellé de la commune"),
        ("Communes", "nb_elus"), ("Communes", "nb_nouveaux"),("Communes", "%"),
        ("EPCI", "nb_elus_epci"), ("EPCI", "nb_nouveaux_epci"),("EPCI", "%"),
    ])

    
    return synthese

def filtrer_elus(elus_municipaux, codes_communes):
    return elus_municipaux[elus_municipaux["Code de la commune"].isin(codes_communes)]
# ---------------------------------------------------------
# Base de données Flux mobilité domicile-lieu de travail (INSEE)
# ---------------------------------------------------------
def charger_donnees_flux():
    base_flux = pd.read_csv('base-flux-mobilite-domicile-lieu-travail-2020.csv',  sep=';', dtype={
        'CODGEO': 'string',
        'LIBGEO': 'string',
        'DCLT': 'string',
        'L_DCLT': 'string',
        'NBFLUX_C20_ACTOCC15P' : 'float64'
    })
    base_flux.CODGEO.astype(str)
    return base_flux

def charger_donnees_flux_modes():
    url = "https://www.data.gouv.fr/api/1/datasets/r/f624e1db-8f22-4a96-9f5a-9f9ee2aae53e"
    return pd.read_csv(url, sep=",", encoding="utf-8", dtype={"geocode_commune": str})  # sep="," au lieu de ";", et on force le code commune en texte

def charger_population_communes():
    # Référentiel national : population et EPCI de rattachement de chaque commune
    resp = requests.get("https://geo.api.gouv.fr/communes", params={"fields": "code,population,codeEpci"})
    return pd.DataFrame(resp.json())


def bracket_population(population):
    # Classe une population dans une tranche, pour comparer des territoires de taille comparable
    if population is None or pd.isna(population):
        return "Inconnu"
    elif population < 2000:
        return "< 2 000 hab."
    elif population < 5000:
        return "2 000 - 5 000 hab."
    elif population < 10000:
        return "5 000 - 10 000 hab."
    elif population < 20000:
        return "10 000 - 20 000 hab."
    elif population < 50000:
        return "20 000 - 50 000 hab."
    elif population < 100000:
        return "50 000 - 100 000 hab."
    else:
        return "> 100 000 hab."


def calculer_repartition(flux_modes, codes):
    # Calcule la répartition modale (%) pour un ensemble de codes commune donné
    data = flux_modes[flux_modes["geocode_commune"].isin(codes)]
    rep = data.groupby("mode_transport", as_index=False)["valeur"].sum()
    total = rep["valeur"].sum()
    rep["pct"] = (rep["valeur"] / total * 100).round(1) if total > 0 else 0
    return rep
def charger_referentiel_epci():
    resp = requests.get("https://geo.api.gouv.fr/communes", params={"fields": "code,codeEpci"})  # récupère toutes les communes de France avec leur code EPCI
    communes_epci = pd.DataFrame(resp.json())  # transforme la réponse JSON en tableau pandas

    resp2 = requests.get("https://geo.api.gouv.fr/epcis", params={"fields": "code,nom"})  # récupère la liste des EPCI avec leur nom
    epcis = pd.DataFrame(resp2.json()).rename(columns={"code": "codeEpci", "nom": "Libellé EPCI destination"})  # met en tableau et renomme les colonnes pour la fusion

    return communes_epci.merge(epcis, on="codeEpci", how="left")  # associe à chaque commune le nom de son EPCI de rattachement

def preparer_regroupement(data_flux, keys_mode_affichage):
    """Affiche le bouton de regroupement (Commune/EPCI) et enrichit les données si besoin."""
    if keys_mode_affichage == "EPCI":
        data_flux = data_flux.merge(charger_referentiel_epci(), left_on="DCLT", right_on="code", how="left")
        colonne_groupe = "Libellé EPCI destination"
    else:
        colonne_groupe = "L_DCLT"
    return data_flux, colonne_groupe


def calculer_tableau_flux(data_flux, colonne_groupe, nb_affichage=10):
    """Regroupe les flux par destination, calcule le pourcentage, garde les plus gros flux."""
    tableau = data_flux.groupby(colonne_groupe, as_index=False).agg(
        NBFLUX_C20_ACTOCC15P=("NBFLUX_C20_ACTOCC15P", "sum")
    )
    tableau["pct"] = (tableau["NBFLUX_C20_ACTOCC15P"] / tableau["NBFLUX_C20_ACTOCC15P"].sum() * 100).round(1)
    return tableau.nlargest(nb_affichage, "NBFLUX_C20_ACTOCC15P")

def preparer_regroupement_origine(data_flux, keys_mode_affichage):
    """Même logique que preparer_regroupement(), mais pour regrouper par origine (CODGEO/LIBGEO) plutôt que par destination (DCLT/L_DCLT)."""
    if keys_mode_affichage == "EPCI":
        referentiel = charger_referentiel_epci().rename(columns={"Libellé EPCI destination": "Libellé EPCI origine"})  # évite un nom de colonne trompeur
        data_flux = data_flux.merge(referentiel, left_on="CODGEO", right_on="code", how="left")
        colonne_groupe = "Libellé EPCI origine"
    else:
        colonne_groupe = "LIBGEO"
    return data_flux, colonne_groupe
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
st.subheader(f"📍 {territoire_label}")

population_totale = sum(c.get("population") or 0 for c in communes_selectionnees)
surface_totale = sum(c.get("surface") or 0 for c in communes_selectionnees)

col1, col2 = st.columns(2)
col1.metric("Population", f"{population_totale:,}".replace(",", " "))
col1.metric("Nombre de communes", len(communes_selectionnees))
col1.metric("Surface (ha)", f"{surface_totale:,.0f}".replace(",", " "))

# Carte : un point par commune du territoire
points = [
    {"lat": c["centre"]["coordinates"][1], "lon": c["centre"]["coordinates"][0]}
    for c in communes_selectionnees
    if "centre" in c
]
if points:
    col2.map(pd.DataFrame(points))

# =========================================================
# ÉTAPE 2 bis : élus municipaux (répertoire national des élus)
# =========================================================
st.divider()
st.markdown(f"# 🗳️ Les élus du territoire et le renouvellement en 2026")

codes_communes = [c["code"] for c in communes_selectionnees]
elus_epci, elus_municipaux = charger_donnees_elus()

st.markdown("#### Synthèse par commune")
st.dataframe(
    calculer_synthese(elus_municipaux, codes_communes)
    .style.background_gradient(axis=0)
    .format({
        ("EPCI", "%"): "{:.0f}",
        ("Communes", "%"): "{:.0f}"
        }))  # mise en forme conditionnelle et 0 chiffre après la virgule
st.write(
    "Au niveau national, le taux de renouvellement des élu.e.s municipaux est de 58%."
    " On observe que le renouvellement est plus faible pour les intercommunalité que pour les communes, ce qui est habituel."
)
with st.expander("#### Voir la liste des élus"):
    st.dataframe(filtrer_elus(elus_municipaux, codes_communes))
st.caption("Données issues du registre national des élu.e.s, si deux élu.e.s de la même communes sont homonyme, ils sont comptés comme étant la même personne.")
# =========================================================
# MOBILITE
# Flux mobilité (issue de la base flux mobilité domicile lieu de travail)
# =========================================================

st.divider()
st.markdown(f"# 🚴La mobilité sur {territoire_label}")

# Chargemnt des données de flux domicile-lieu de travail
codes_communes = [c["code"] for c in communes_selectionnees]
base_flux = charger_donnees_flux()
base_flux_territoire = base_flux[base_flux["CODGEO"].isin(codes_communes)]  # filtre commun aux deux modes, calculé une seule fois
# --- Calcul des flux internes au territoire ---
flux_internes = base_flux_territoire[base_flux_territoire["DCLT"].isin(codes_communes)]
nb_flux_internes = flux_internes["NBFLUX_C20_ACTOCC15P"].sum()
nb_flux_total = base_flux_territoire["NBFLUX_C20_ACTOCC15P"].sum()
pct_flux_internes = round(nb_flux_internes / nb_flux_total * 100, 1) if nb_flux_total > 0 else 0

# --- Seule vraie différence entre les deux modes : le libellé affiché ---
label_metrique = "Actifs travaillant dans leur commune" if type_territoire == "Commune" else "Flux internes (nombre d'actifs)"

# importation de la base de flux par destination et par origine
base_flux_destination = base_flux[base_flux["DCLT"].isin(codes_communes)]  # garde les flux dont la destination (lieu de travail) est le territoire sélectionné

flux_internes_dest = base_flux_destination[base_flux_destination["CODGEO"].isin(codes_communes)]
nb_flux_internes_dest = flux_internes_dest["NBFLUX_C20_ACTOCC15P"].sum()
nb_flux_total_dest = base_flux_destination["NBFLUX_C20_ACTOCC15P"].sum()
pct_flux_internes_dest = round(nb_flux_internes_dest / nb_flux_total_dest * 100, 1) if nb_flux_total_dest > 0 else 0

label_metrique_dest = "Actifs qui habitent et travaillent sur place" if type_territoire == "Commune" else "Flux internes (nombre d'actifs)"


# Affichage des trois colonnes : flux internes, flux par destination, flux par origine

col4, col5, col6bis = st.columns(3)
col4.metric(
    label=label_metrique,
    value=f"{nb_flux_internes:,.0f}".replace(",", " "),
    delta=f"{pct_flux_internes} %",
)
nb_affichage = col4.slider("Combien de territoires voulez-vous afficher ?", 0, 20, 5, key="slider_flux")
mode_affichage = col4.radio("Regrouper les flux par :", ["Commune", "EPCI"], horizontal=True, key="mode_flux")
with col4:

    base_flux_territoire, colonne_groupe = preparer_regroupement(base_flux_territoire, keys_mode_affichage=mode_affichage)
    base_flux_destination, colonne_groupe_origine = preparer_regroupement_origine(base_flux_destination,  keys_mode_affichage=mode_affichage)

tableau_flux = calculer_tableau_flux(base_flux_territoire, colonne_groupe, nb_affichage)


col5.markdown("#### 🗺️ Où travaillent les habitants ?")

for _, ligne in tableau_flux.iterrows():
    col5.write(f"**{ligne[colonne_groupe]}** : {ligne['NBFLUX_C20_ACTOCC15P']:,.0f} actifs ({ligne['pct']} %)".replace(",", " "))
    col5.progress(ligne["pct"] / 100)

col6bis.markdown("#### 🚩 D'où viennent les gens qui y-travaillent ?")

tableau_flux_origine = calculer_tableau_flux(base_flux_destination, colonne_groupe_origine, nb_affichage)
for _, ligne in tableau_flux_origine.iterrows():
    col6bis.write(f"**{ligne[colonne_groupe_origine]}** : {ligne['NBFLUX_C20_ACTOCC15P']:,.0f} actifs ({ligne['pct']} %)".replace(",", " "))
    col6bis.progress(ligne["pct"] / 100)






# =========================================================
# MOBILITE
# Modes de déplacements
# =========================================================
st.markdown(f"## Comment les habitants de {territoire_label} se déplacent-ils ?")
st.subheader("🚗 Répartition modale des déplacements domicile-travail")
flux_modes = charger_donnees_flux_modes()
flux_modes_territoire = flux_modes[flux_modes["geocode_commune"].isin(codes_communes)]  # garde les communes du territoire sélectionné
population_communes = charger_population_communes()

flux_modes_territoire = flux_modes[flux_modes["geocode_commune"].isin(codes_communes)]

if flux_modes_territoire.empty:
    st.info("Pas de données de répartition modale disponibles pour ce territoire.")
else:
    # --- Territoire sélectionné ---
    rep_territoire = calculer_repartition(flux_modes, codes_communes)
    rep_territoire["Territoire"] = territoire_label

    # --- Moyenne nationale ---
    rep_national = calculer_repartition(flux_modes, flux_modes["geocode_commune"].unique())
    rep_national["Territoire"] = "France entière"

    # --- Détermination de la tranche de population du territoire sélectionné ---
    if type_territoire == "Commune":
        population_ref = communes_selectionnees[0].get("population") or 0
    else:
        population_ref = population_totale  # déjà calculée plus haut pour l'EPCI

    tranche_cible = bracket_population(population_ref)

    # --- Recherche des territoires similaires (même tranche de population) ---
    if type_territoire == "Commune":
        population_communes["tranche"] = population_communes["population"].apply(bracket_population)
        codes_similaires = population_communes[
            (population_communes["tranche"] == tranche_cible)
            & (~population_communes["code"].isin(codes_communes))
        ]["code"].tolist()
    else:
        pop_par_epci = population_communes.groupby("codeEpci", as_index=False)["population"].sum()
        pop_par_epci["tranche"] = pop_par_epci["population"].apply(bracket_population)
        epci_similaires = pop_par_epci[
            (pop_par_epci["tranche"] == tranche_cible) & (pop_par_epci["codeEpci"] != epci["code"])
        ]["codeEpci"].tolist()
        codes_similaires = population_communes[
            population_communes["codeEpci"].isin(epci_similaires)
        ]["code"].tolist()

    if codes_similaires:
        rep_similaires = calculer_repartition(flux_modes, codes_similaires)
        rep_similaires["Territoire"] = f"Territoires similaires ({tranche_cible})"
    else:
        rep_similaires = pd.DataFrame(columns=["mode_transport", "valeur", "pct", "Territoire"])

    # --- Fusion des trois séries et graphique groupé ---
    comparatif = pd.concat([rep_territoire, rep_similaires, rep_national], ignore_index=True)
    # --- Détermine l'ordre des modes de transport à partir du territoire sélectionné (ordre décroissant) ---
    ordre_modes = rep_territoire.sort_values("pct", ascending=False)["mode_transport"].tolist()  # liste des modes du plus au moins utilisé

    # --- Affichage des trois colonnes avec barres de progression, dans le même ordre ---
    col1, col2, col3 = st.columns(3)

    for col, rep, titre in [
        (col1, rep_territoire, territoire_label),
        (col2, rep_similaires, f"Territoires similaires ({tranche_cible})"),
        (col3, rep_national, "France entière"),
    ]:
        with col:
            st.write(f"**{titre}**")
            if rep.empty:  # cas des territoires similaires introuvables
                st.info("Pas de donnée disponible.")
            else:
                rep_ordonne = rep.set_index("mode_transport").reindex(ordre_modes).reset_index()  # réordonne selon ordre_modes, même s'il manque un mode
                rep_ordonne["pct"] = rep_ordonne["pct"].fillna(0)  # remplace par 0 si un mode est absent pour ce territoire
                for _, ligne in rep_ordonne.iterrows():
                    st.write(f"{ligne['mode_transport']} — {ligne['pct']} %")
                    st.progress(ligne["pct"] / 100)

    # --- Mention de la source et de la date de mise à jour ---
    date_maj = pd.to_datetime(flux_modes["date_mesure"]).max().strftime("%d/%m/%Y")  # date la plus récente présente dans le jeu de données
    st.caption(
        f"Source : [data.gouv.fr - Flux domicile-travail selon le mode de transport principal utilisé]"
        f"(https://www.data.gouv.fr/datasets/flux-domicile-travail-selon-le-mode-de-transport-principal-utilise) "
        f"(INSEE / Tableau de bord des mobilités durables) — données au {date_maj}"
    )
    

    
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

# =========================================================
# FIN DE PAGE
# =========================================================
st.divider()
st.subheader("Infos sur cette page")

# Temps écoulé
elapsed = time.time() - st.session_state.start_time
st.write(f"Temps de chargement de la page : {elapsed:.1f} secondes")
st.write("Les données inscrite sur cette pages se basent sur des données publiques librement accessible. Le code, l'analyse et la mise en page est la propriété de Tristan Riom")