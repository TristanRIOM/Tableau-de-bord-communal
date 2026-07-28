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

# ---------------------------------------------------------
# DONNÉES CLIMATIQUES (Canicules, projections)
# ---------------------------------------------------------
@st.cache_data(ttl=3600)  # Cache 1h pour la vigilance (données temps réel)
def charger_vigilance_canicule(codes_departements):
    """Récupère la vigilance canicule pour les départements du territoire."""
    # Liste des codes départements du territoire
    if type_territoire == "Commune":
        deps = [c["codeDepartement"] for c in communes_selectionnees if "codeDepartement" in c]
    else:
        deps = list(set([c["codeDepartement"] for c in communes_selectionnees if "codeDepartement" in c]))

    if not deps:
        return None

    # Appel API Vigilance Météo-France (format JSON)
    url = "https://vigilance.meteofrance.com/data/NXFR/vigilance/encours/couleur/departement"
    try:
        resp = requests.get(url, timeout=10)
        vigilance_data = resp.json() if resp.status_code == 200 else None
    except:
        vigilance_data = None

    if not vigilance_data:
        st.warning("⚠️ Impossible de récupérer les données de vigilance Météo-France.")
        return None

    # Filtre pour les départements du territoire
    vigilance_territoire = []
    for dep in deps:
        dep_str = dep.zfill(3)  # Format "001" pour Ain, "075" pour Paris, etc.
        if dep_str in vigilance_data:
            couleur = vigilance_data[dep_str]["couleur"]
            vigilance_territoire.append({"département": dep, "couleur": couleur})

    return vigilance_territoire

def charger_donnees_canicules_historiques():
    """Charge un CSV local avec le nombre de jours de canicule par département (1991-2020).
    Source : STATCLIM / ADEME (données moyennes sur 30 ans).
    Format attendu : 'departement;nom;jours_canicule_1991_2020;nuits_tropicales_1991_2020'
    """
    try:
        return pd.read_csv("donnees_climat/canicules_historiques_departements.csv", sep=";", dtype=str)
    except FileNotFoundError:
        st.warning("⚠️ Fichier 'canicules_historiques_departements.csv' manquant. Téléchargez-le depuis [STATCLIM](https://www.statistiques.developpement-durable.gouv.fr/).")
        return None

def charger_projections_canicules():
    """Charge les projections DRIAS pour les canicules (scénarios RCP 4.5 et 8.5).
    Format attendu : 'departement;annee;scenario;jours_canicule;nuits_tropicales'
    """
    try:
        return pd.read_csv("donnees_climat/projections_canicules_drias.csv", sep=";", dtype={"annee": str})
    except FileNotFoundError:
        st.warning("⚠️ Fichier 'projections_canicules_drias.csv' manquant. Utilisez des données simplifiées pour la démo.")
        # Données de démo pour éviter les erreurs
        return pd.DataFrame({
            "departement": ["001", "075", "069"],  # Ain, Paris, Rhône
            "annee": ["2030", "2050", "2100"],
            "scenario": ["RCP4.5", "RCP4.5", "RCP4.5", "RCP8.5", "RCP8.5", "RCP8.5"],
            "jours_canicule": [10, 15, 25, 15, 25, 40],
            "nuits_tropicales": [2, 5, 10, 5, 15, 30]
        })

def get_couleur_vigilance(couleur):
    """Retourne l'emoji et le texte pour une couleur de vigilance."""
    mapping = {
        "vert": ("✅", "Aucune vigilance"),
        "jaune": ("🟡", "Canicule possible"),
        "orange": ("🟠", "Canicule avérée"),
        "rouge": ("🔴", "Canicule dangereuse"),
    }
    return mapping.get(couleur, ("⚪", "Non renseigné"))
# ---------------------------------------------------------
# DOCUMENTS STRUCTURANTS (PLU, POS, PCAET)
# ---------------------------------------------------------
def afficher_pcaet_nantes(SIREN):
    url = "https://www.data.gouv.fr/api/1/datasets/r/beefe76c-1fa6-46c7-9a4f-466c96c5579f"
    df = pd.read_csv(url, sep=";", encoding="utf-8-sig")

    # Convertir la colonne SIREN en string puis ne garde que les 9 premier caracteres (l'ademe a rajouté des ".0" a la fin des SIREN)
    df["SIREN collectivites_coporteuses"] = df["SIREN collectivites_coporteuses"].astype(str)
    df["SIREN collectivites_coporteuses"] = df["SIREN collectivites_coporteuses"].str[:9]  # On ne garde que les 9 premiers caractères du SIREN (parfois il y a des espaces ou des suffixes)

    # Filtrer UNIQUEMENT par SIREN (plus fiable)
    pcaet_nantes = df[df["SIREN collectivites_coporteuses"] == str(SIREN)]

    if len(pcaet_nantes) > 0:
        st.write("✅ PCAET trouvé :\n")
        ligne = pcaet_nantes.iloc[0]
        for colonne in [
            "Collectivités porteuses", "SIREN collectivites_coporteuses", "Type_demarche", "Nom",
            "Description_rapide", "Date_creation", "Date_lancement", "Demarche_etat",
            "Population_couverte", "Chef_de_projet", "Contact", "Elu_referent"
        ]:
            st.write(f"{colonne}: {ligne[colonne]}")
    else:
        st.write(f"❌ Aucune donnée trouvée pour le SIREN {SIREN}.")



def get_documents_urbanisme(code_insee):
    """Récupère les documents d'urbanisme (PLU, POS, etc.) pour une commune via l'API IGN."""
    # 1. Récupérer le contour de la commune
    resp = requests.get(
        f"https://geo.api.gouv.fr/communes/{code_insee}",
        params={"fields": "contour"},
    )

    if resp.status_code != 200:
        st.error(f"❌ Impossible de récupérer le contour de la commune {code_insee}")
        return None

    data = resp.json()
    if "contour" not in data:
        st.error(f"❌ Contour non trouvé pour la commune {code_insee}")
        return None

    contour = data["contour"]

    # 2. Interroger le Géoportail Urbanisme avec cette géométrie
    resp_gpu = requests.get(
        "https://apicarto.ign.fr/api/gpu/document",
        params={"geom": str(contour).replace("'", '"')},
    )

    if resp_gpu.status_code != 200:
        st.warning(f"⚠️ API GPU indisponible (status {resp_gpu.status_code})")
        return None

    try:
        return resp_gpu.json()
    except Exception as e:
        st.warning(f"⚠️ Réponse GPU non valide: {e}")
        return None


# =========================================================
# SELECTION DU TERRITOIRE
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
                "https://geo.api.gouv.fr/communes", # Pour info, structure de la donnée : "nom":"L'Abergement-Clémenciat", "code":"01001", "codeDepartement":"01", "siren":"210100012", "codeEpci":"200069193", "codeRegion":"84", "codesPostaux": ["01400"],"population":860
                params={
                    "nom": nom_recherche,
                    "fields": "nom,code,codeDepartement,codeRegion,population,centre,surface,codeEpci,siren",
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
            SIREN = commune["siren"]

else:  # EPCI
    nom_epci = st.text_input(
        "Nom de la communauté de communes / agglomération",
        placeholder="ex : Grand Chalon",
    )

    if nom_epci:
        with st.spinner("Recherche en cours..."):
            resp = requests.get(
                "https://geo.api.gouv.fr/epcis", # Pour info, structure de la donnée :  "nom":"CC Faucigny - Glières", "code":"200000172", "codesDepartements":["74"], "codesRegions":["84"],"population":28363
                params={"nom": nom_epci, "fields": "nom,code,population,code", "boost": "population"},
            )
        epcis = resp.json() if resp.status_code == 200 else []

        if not epcis:
            st.warning("Aucun EPCI trouvé avec ce nom.")
        else:
            noms_affiches = [e["nom"] for e in epcis]
            choix = st.selectbox("Sélectionnez l'EPCI exact", noms_affiches)
            epci = epcis[noms_affiches.index(choix)]
            territoire_label = epci["nom"]
            SIREN = epci["code"]

            with st.spinner("Récupération des communes membres..."):
                resp2 = requests.get(
                    f"https://geo.api.gouv.fr/epcis/{epci['code']}/communes",
                    params={"fields": "nom,code,codeDepartement,population,centre,surface,codeEpci"},
                )
            communes_selectionnees = resp2.json() if resp2.status_code == 200 else []
            st.caption(f"{len(communes_selectionnees)} communes membres")

# =========================================================
# AFFICHAGE DES INFORMATIONS DE BASES SUR LE TERRITOIRE
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
# AFFICHAGE DES ÉLUS MUNICIPAUX
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
# MOBILITE #1
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
# MOBILITE #2
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
        # Obtenir le code EPCI du territoire sélectionné
        current_epci_code = communes_selectionnees[0].get("codeEpci") if communes_selectionnees else None
        if current_epci_code:
            pop_par_epci = population_communes.groupby("codeEpci", as_index=False)["population"].sum()
            pop_par_epci["tranche"] = pop_par_epci["population"].apply(bracket_population)
            epci_similaires = pop_par_epci[
                (pop_par_epci["tranche"] == tranche_cible) & (pop_par_epci["codeEpci"] != current_epci_code)
            ]["codeEpci"].tolist()
            codes_similaires = population_communes[
                population_communes["codeEpci"].isin(epci_similaires)
            ]["code"].tolist()
        else:
            codes_similaires = []

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
# DOCUMENTS STRUCTURANTS
# =========================================================
st.divider()
st.markdown(f"# 📄 Documents structurants")

# --- PCAET v2 (NOUVELLE VERSION ADEME) ---
st.subheader("🌍 Plans Climat-Air-Énergie Territorial (PCAET) v2")

# SIREN = requests.get(f"https://geo.api.gouv.fr/{('communes' if type_territoire=='Commune' else 'epcis')}/{communes_selectionnees[0][('code' if type_territoire=='Commune' else 'codeEpci')]}").json().get("siren")

st.write(f"SIREN de la collectivité séléctionnée : {SIREN}")
afficher_pcaet_nantes(SIREN)

# --- Documents d'urbanisme (PLU, POS, etc.) ---
st.subheader("🏗️ Documents d'urbanisme")

if communes_selectionnees:
    code_insee = communes_selectionnees[0]["code"]

    with st.spinner("Recherche des documents d'urbanisme en cours..."):
        docs_urbanisme = get_documents_urbanisme(code_insee)

    if docs_urbanisme and isinstance(docs_urbanisme, dict) and "features" in docs_urbanisme:
        st.success(f"✅ {len(docs_urbanisme['features'])} documents trouvés !")

        # Création d'un tableau lisible
        documents = []
        for doc in docs_urbanisme["features"]:
            props = doc.get("properties", {})
            documents.append({
                "Type": props.get("typeDocument", "Non spécifié"),
                "Nom": props.get("nom", "Non spécifié"),
                "Date": props.get("dateApprobation", props.get("date", "Non spécifiée")),
                "Statut": props.get("statut", "Non spécifié"),
                "Lien": props.get("url", "#")
            })

        if documents:
            df_docs = pd.DataFrame(documents)
            st.dataframe(df_docs, use_container_width=True)
    else:
        st.info("⚠️ Aucun document trouvé via l'API. Essayez le lien direct ci-dessous.")
        st.markdown(f"[🔍 Voir sur le Géoportail Urbanisme](https://www.geoportail-urbanisme.gouv.fr/map/#/search?codeInsee={code_insee})")
else:
    st.info("Sélectionnez un territoire pour afficher les documents structurants")

# =========================================================
# VULNÉRABILITÉ CLIMATIQUE
# Données météorologiques et projections climatiques
# =========================================================

st.divider()
st.markdown(f"# Données météorologiques et projections climatiques pour {territoire_label}")
# =========================================================
# CLIMAT : CANICULES ET PROJECTIONS
# =========================================================
st.divider()
st.markdown(f"# 🌡️ Climat : Canicules et projections pour {territoire_label}")

# --- 1. Vigilance canicule (aujourd'hui) ---
st.subheader("🔥 Vigilance canicule **aujourd’hui**")
if communes_selectionnees:
    codes_departements = list(set([c["codeDepartement"] for c in communes_selectionnees if "codeDepartement" in c]))
    vigilance = charger_vigilance_canicule(codes_departements)

    if vigilance:
        col1, col2 = st.columns([1, 3])
        with col1:
            # Affichage global
            couleurs = [v["couleur"] for v in vigilance]
            if all(c == "vert" for c in couleurs):
                st.success("✅ **Aucune vigilance canicule** sur le territoire.")
            else:
                max_couleur = max(couleurs, key=lambda x: ["vert", "jaune", "orange", "rouge"].index(x))
                emoji, texte = get_couleur_vigilance(max_couleur)
                st.error(f"{emoji} **{texte}** sur une partie du territoire.")

        with col2:
            st.markdown("**Détail par département :**")
            for v in vigilance:
                emoji, texte = get_couleur_vigilance(v["couleur"])
                st.write(f"- **Département {v['département']}** : {emoji} {texte}")
    else:
        st.info("⚠️ Données de vigilance non disponibles (territoire hors métropole ?).")
else:
    st.info("Sélectionnez un territoire pour afficher la vigilance canicule.")

# --- 2. Données historiques (1991-2020) ---
st.divider()
st.subheader("📊 **Données historiques (1991-2020)**")

donnees_historiques = charger_donnees_canicules_historiques()
if donnees_historiques is not None and communes_selectionnees:
    codes_departements = list(set([c["codeDepartement"] for c in communes_selectionnees if "codeDepartement" in c]))
    departements_territoire = [dep.zfill(3) for dep in codes_departements]

    # Filtre les données pour le territoire
    hist_territoire = donnees_historiques[donnees_historiques["departement"].isin(departements_territoire)]

    if not hist_territoire.empty:
        # Moyenne pour le territoire
        mean_jours = hist_territoire["jours_canicule_1991_2020"].astype(float).mean()
        mean_nuits = hist_territoire["nuits_tropicales_1991_2020"].astype(float).mean()

        col1, col2 = st.columns(2)
        col1.metric("🔥 Jours de canicule/an (moyenne 1991-2020)", f"{mean_jours:.1f}")
        col2.metric("🌙 Nuits tropicales/an (moyenne 1991-2020)", f"{mean_nuits:.1f}")

        # Comparaison avec la France (valeurs moyennes nationales)
        st.caption("""
        *Source : [STATCLIM / ADEME](https://www.statistiques.developpement-durable.gouv.fr/indicateurs-indices/f/2584/0/jours-vague-chaleur).
        Moyenne nationale : ~5 jours de canicule/an (1991-2020).*""")
    else:
        st.warning("Aucune donnée historique disponible pour ce territoire.")
else:
    st.warning("Données historiques non chargées.")

# --- 3. Projections futures (DRIAS) ---
st.divider()
st.subheader("🔮 **Projections futures (2030-2100)**")

projections = charger_projections_canicules()
if projections is not None and communes_selectionnees:
    codes_departements = [dep.zfill(3) for dep in list(set([c["codeDepartement"] for c in communes_selectionnees if "codeDepartement" in c]))]
    proj_territoire = projections[projections["departement"].isin(codes_departements)]

    if not proj_territoire.empty:
        # Filtre pour le territoire et regroupe par année/scenario
        proj_territoire["annee"] = proj_territoire["annee"].astype(int)
        proj_territoire["jours_canicule"] = proj_territoire["jours_canicule"].astype(float)
        proj_territoire["nuits_tropicales"] = proj_territoire["nuits_tropicales"].astype(float)

        # Graphique : Évolution des jours de canicule
        fig = px.line(
            proj_territoire,
            x="annee",
            y="jours_canicule",
            color="scenario",
            title=f"Projection du nombre de jours de canicule/an pour {territoire_label}",
            labels={"jours_canicule": "Jours de canicule/an", "annee": "Année", "scenario": "Scénario"},
            color_discrete_map={"RCP4.5": "orange", "RCP8.5": "red"}
        )
        fig.update_layout(hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        # Graphique : Nuits tropicales
        fig2 = px.bar(
            proj_territoire,
            x="annee",
            y="nuits_tropicales",
            color="scenario",
            barmode="group",
            title=f"Projection du nombre de nuits tropicales/an pour {territoire_label}",
            labels={"nuits_tropicales": "Nuits tropicales/an", "annee": "Année", "scenario": "Scénario"},
            color_discrete_map={"RCP4.5": "orange", "RCP8.5": "red"}
        )
        st.plotly_chart(fig2, use_container_width=True)

        st.caption("""
        *Source : [DRIAS](https://www.drias-climat.fr/) (scénarios RCP4.5 = +2°C en 2100, RCP8.5 = +4°C).
        Une **nuit tropicale** = température nocturne ≥ 20°C.*""")
    else:
        st.warning("Aucune projection disponible pour ce territoire.")
else:
    st.warning("Projections non chargées.")

# =========================================================
# FIN DE PAGE
# =========================================================
st.divider()
st.subheader("📚 Sources & Crédits")
# Colonnes pour organiser les sources
col1, col2 = st.columns(2)
with col1:
    st.markdown("""
    **🏛️ Données publiques utilisées par thématiques**
    
    - 🗳️ **[Répertoire des élus](https://www.data.gouv.fr/fr/datasets/repertoire-national-des-elus-2/)** – Ministère de l'Intérieur
    - 📊 **[Flux mobilité INSEE](https://www.data.gouv.fr/fr/datasets/flux-domicile-travail-2020/)** – INSEE 2020
    - 🚗 **[Modes de transport](https://www.data.gouv.fr/datasets/flux-domicile-travail-selon-le-mode-de-transport-principal-utilise)** – INSEE / ADEME

    """)

with col2:
    st.markdown("""
    **📍 Données générales sur les territoires**
    
    - 📈 **[Population](https://geo.api.gouv.fr/)** – INSEE via API Geo
    - 🔗 **[data.gouv.fr](https://www.data.gouv.fr/)** – Plateforme open data française
    - 🗺️ **[Géographie](https://geo.api.gouv.fr/)** – API Geo (DINUM)
    
    Développé avec [Streamlit](https://streamlit.io/)
    """)
# Temps écoulé
elapsed = time.time() - st.session_state.start_time
st.caption(f"⏱️ Temps de chargement : {elapsed:.1f} secondes")
st.write("""
*Code, analyse et mise en page : Tristan Riom | Dernière mise à jour :* """ + datetime.now().strftime("%d/%m/%Y"))