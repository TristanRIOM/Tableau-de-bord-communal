# Scripts de récupération des données PCAET v2 de l'ADEME

Ce dossier contient des scripts Python pour récupérer les données **PCAET v2** (Plans Climat-Air-Énergie Territorial) depuis [data.gouv.fr](https://www.data.gouv.fr/fr/datasets/pcaet-v2-demarches-partie-1-entete/) à partir d'un code commune (INSEE) ou d'un code EPCI (intercommunalité).

## 📁 Fichiers disponibles

1. **`adev_pcaet_downloader.py`** - Version complète avec classe et gestion avancée du cache
2. **`adev_pcaet_simple.py`** - Version simplifiée pour une intégration directe dans Streamlit

## 🎯 Fonctionnalités

- ✅ Téléchargement automatique depuis l'API data.gouv.fr
- ✅ Filtrage par **code INSEE** (commune) ou **code SIREN** (EPCI)
- ✅ Gestion du cache pour éviter les téléchargements répétés
- ✅ Intégration facile avec Streamlit (compatibilité avec `@st.cache_data`)
- ✅ Gestion des erreurs et URLs alternatives
- ✅ Affichage des données dans un format adapté à Streamlit

## 🔧 Installation

### Prérequis

```bash
pip install pandas requests streamlit
```

### Utilisation

#### Option 1: Utilisation de la version complète (classe)

```python
from adev_pcaet_downloader import ADEMEPCAETDownloader

# Créer une instance
downloader = ADEMEPCAETDownloader(cache_dir="./cache", cache_ttl=3600)

# Récupérer toutes les données
all_data = downloader.get_all_data()

# Filtrer par commune (code INSEE)
commune_data = downloader.filter_by_commune("69001")  # Lyon

# Filtrer par EPCI (code SIREN)
epci_data = downloader.filter_by_epci("200069785")  # Métropole de Lyon

# Obtenir un résumé
summary = downloader.get_summary(codes_communes=["69001"])
```

#### Option 2: Utilisation de la version simplifiée (fonctions directes)

```python
from adev_pcaet_simple import (
    charger_pcaet_v2_par_commune,
    charger_pcaet_v2_par_epci,
    charger_tous_pcaet_v2,
    afficher_pcaet_territoire
)

# Dans votre code Streamlit
import streamlit as st

# Pour une commune
code_insee = "69001"  # Lyon
pcaet_data = charger_pcaet_v2_par_commune(code_insee)
afficher_pcaet_territoire(pcaet_data, "Lyon")

# Pour un EPCI
code_epci = "200069785"  # Métropole de Lyon
pcaet_data = charger_pcaet_v2_par_epci(code_epci)
afficher_pcaet_territoire(pcaet_data, "Métropole de Lyon")
```

## 📖 Intégration dans `app.py`

### Modifications recommandées pour votre `app.py`

Remplacez ou complétez la section **DOCUMENTS STRUCTURANTS** de votre app.py :

```python
# =========================================================
# DOCUMENTS STRUCTURANTS
# =========================================================
st.divider()
st.markdown(f"# 📄 Documents structurants")

# Importer les fonctions PCAET
from adev_pcaet_simple import (
    charger_pcaet_v2_par_commune,
    charger_pcaet_v2_par_epci,
    afficher_pcaet_territoire
)

# --- PCAET v2 (nouvelle version) ---
st.subheader("🌍 Plans Climat-Air-Énergie Territorial (PCAET) v2")

if communes_selectionnees:
    if type_territoire == "Commune":
        code_insee = communes_selectionnees[0]["code"]
        pcaet_v2_data = charger_pcaet_v2_par_commune(code_insee)
    else:
        code_epci = communes_selectionnees[0]["codeEpci"]
        pcaet_v2_data = charger_pcaet_v2_par_epci(code_epci)
    
    afficher_pcaet_territoire(pcaet_v2_data, territoire_label)
    
    # Afficher aussi l'ancienne version pour comparaison
    st.markdown("---")
    st.markdown("#### Version précédente (PCAET v1)")
    # ... votre code existant pour PCAET v1 ...

else:
    st.info("Sélectionnez un territoire pour afficher les PCAET v2")
```

## 📊 Données disponibles

Le dataset PCAET v2 contient les informations suivantes :

### Champs principaux
- **Nom de la collectivité** : Nom de la collectivité porteuse du PCAET
- **SIREN** : Identifiant SIREN de la collectivité
- **Type de PCAET** : Type de démarche (PCAET, PCAET simplifié, etc.)
- **Statut de la démarche** : En cours, approuvé, etc.
- **Date de lancement** : Date de lancement de la démarche
- **Date d'approbation** : Date d'approbation officielle
- **Date de dernière mise à jour** : Date de la dernière mise à jour
- **Lien vers le PCAET** : URL vers le document complet
- **Lien vers la délibération** : URL vers la délibération

### Champs géographiques
- **Code INSEE commune** : Code commune porteuse
- **Nom commune** : Nom de la commune
- **SIREN EPCI** : Code SIREN de l'intercommunalité
- **Nom EPCI** : Nom de l'EPCI

## 🔍 URL des données

- **URL principale** : `https://www.data.gouv.fr/dataservices/pcaet-v2-demarches-partie-1-entete`
- **Page du dataset** : [PCAET v2 - Démarches (Partie 1: En-tête)](https://www.data.gouv.fr/fr/datasets/pcaet-v2-demarches-partie-1-entete/)

## 💡 Conseils

1. **Cache** : Utilisez toujours `@st.cache_data` ou la gestion de cache de la classe pour éviter de télécharger les données à chaque interaction utilisateur.

2. **Timeout** : Le téléchargement peut prendre quelques secondes (jusqu'à 30-60s pour le fichier complet).

3. **Erreurs** : Si une URL ne fonctionne pas, le script essaie automatiquement des URLs alternatives.

4. **Codes normalisés** : Les codes INSEE sont normalisés sur 5 chiffres (ex: "69001") et les SIREN sur 9 chiffres.

5. **Données manquantes** : Certaines communes/EPCI peuvent ne pas avoir de PCAET publié.

## 🐛 Résolution des problèmes

### Problème : "Impossible de trouver l'URL du CSV"

**Solution** : Vérifiez que l'URL `https://www.data.gouv.fr/dataservices/pcaet-v2-demarches-partie-1-entete` est accessible. Le format de la réponse peut avoir changé.

### Problème : "Aucun PCAET trouvé"

**Solutions possibles** :
- Vérifiez le code INSEE ou SIREN
- La collectivité n'a peut-être pas encore publié son PCAET v2
- Essayez de consulter manuellement : [data.gouv.fr](https://www.data.gouv.fr/fr/datasets/pcaet-v2-demarches-partie-1-entete/)

### Problème : Téléchargement lent

**Solution** : Utilisez la gestion de cache avec une durée plus longue (ex: `cache_ttl=86400` pour 24h).

## 📞 Support

Pour toute question ou problème, vérifiez d'abord :
- La page du dataset sur [data.gouv.fr](https://www.data.gouv.fr/fr/datasets/pcaet-v2-demarches-partie-1-entete/)
- Le format des codes (INSEE = 5 chiffres, SIREN = 9 chiffres)
- Votre connexion internet

## 📝 Changelog

- **2026-07-27** : Version initiale
  - Support de l'URL `https://www.data.gouv.fr/dataservices/pcaet-v2-demarches-partie-1-entete`
  - Filtrage par commune et EPCI
  - Intégration Streamlit
  - Gestion du cache

## 🎓 Exemples complets

### Exemple 1: Afficher tous les PCAET d'un département

```python
downloader = ADEMEPCAETDownloader()
all_data = downloader.get_all_data()

# Filtrer par département (ex: Rhône = 69)
rhone_data = all_data[all_data['Code département'] == '69']
print(f"Nombre de PCAET dans le Rhône: {len(rhone_data)}")
```

### Exemple 2: Statistiques par statut

```python
downloader = ADEMEPCAETDownloader()
all_data = downloader.get_all_data()

if 'Statut de la démarche' in all_data.columns:
    stats = all_data['Statut de la démarche'].value_counts()
    print("Répartition par statut:")
    print(stats)
```

### Exemple 3: Vérifier si une commune a un PCAET approuvé

```python
downloader = ADEMEPCAETDownloader()
commune_data = downloader.filter_by_commune("69001")  # Lyon

if not commune_data.empty:
    has_approved = "approuvé" in commune_data['Statut de la démarche'].str.lower().values
    print(f"Lyon a un PCAET approuvé: {has_approved}")
```

## 📄 Licence

Ces scripts sont fournis sous licence **MIT**. Vous êtes libre de les utiliser, modifier et redistribuer.

## 🙏 Remerciements

- [ADEME](https://www.ademe.fr/) pour la publication des données
- [data.gouv.fr](https://www.data.gouv.fr/) pour l'hébergement des datasets
- [Streamlit](https://streamlit.io/) pour le framework d'application web
