#!/usr/bin/env python3
"""
Script simplifié pour récupérer les données PCAET v2 de l'ADEME
à intégrer directement dans app.py

Ce script utilise l'URL directe du service de données:
https://www.data.gouv.fr/dataservices/pcaet-v2-demarches-partie-1-entete

Auteur: Tristan Riom
Date: 2026-07-27
"""

import requests
import pandas as pd
from typing import Optional, Union
import streamlit as st


@st.cache_data(ttl=86400)  # Cache 24h
def charger_pcaet_v2_par_commune(code_insee: str) -> Optional[pd.DataFrame]:
    """
    Charge les données PCAET v2 pour une commune spécifique.
    
    Args:
        code_insee: Code INSEE de la commune (ex: "69001" pour Lyon)
    
    Returns:
        DataFrame avec les données PCAET ou None si erreur
    """
    code_insee = str(code_insee).zfill(5)
    
    # Liste des URLs à essayer (par ordre de priorité)
    urls_to_try = [
        "https://www.data.gouv.fr/fr/datasets/r/ce0c5ed8-ac25-4f24-af28-ab8e92b44c09",  # URL directe CSV connue
        "https://www.data.gouv.fr/dataservices/pcaet-v2-demarches-partie-1-entete",  # URL du service
        "https://www.data.gouv.fr/fr/datasets/r/50070596-2c92-4758-a655-0f720079ac62",  # URL alternative
    ]
    
    for url in urls_to_try:
        try:
            with st.spinner(f"Téléchargement des données PCAET pour la commune {code_insee}..."):
                response = requests.get(url, timeout=30)
                
                if response.status_code != 200:
                    continue
                
                # Vérifier si c'est du CSV
                if response.headers.get('Content-Type', '').startswith('text/csv') or url.endswith('.csv'):
                    try:
                        df = pd.read_csv(
                            url,
                            sep=";",
                            dtype=str,
                            encoding="utf-8",
                            on_bad_lines="warn"
                        )
                        # Filtrer par code INSEE
                        filtered_df = _filter_pcaet_by_commune(df, code_insee)
                        if filtered_df is not None:
                            return filtered_df
                    except Exception:
                        continue
                
                # Vérifier si c'est du JSON
                if response.headers.get('Content-Type', '').startswith('application/json'):
                    try:
                        # Vérifier que la réponse n'est pas vide
                        if not response.text.strip():
                            continue
                        data = response.json()
                        csv_url = None
                        
                        if isinstance(data, dict):
                            if 'resources' in data:
                                for resource in data['resources']:
                                    if resource.get('format', '').lower() == 'csv' and 'url' in resource:
                                        csv_url = resource['url']
                                        break
                            elif 'url' in data:
                                csv_url = data['url']
                        
                        if csv_url:
                            df = pd.read_csv(
                                csv_url,
                                sep=";",
                                dtype=str,
                                encoding="utf-8",
                                on_bad_lines="warn"
                            )
                            filtered_df = _filter_pcaet_by_commune(df, code_insee)
                            if filtered_df is not None:
                                return filtered_df
                    except Exception:
                        continue
                        
        except Exception:
            continue
    
    # Si toutes les URLs ont échoué
    st.error(f"❌ Impossible de télécharger les données PCAET v2. Toutes les URLs ont échoué.")
    return None


def _filter_pcaet_by_commune(df: pd.DataFrame, code_insee: str) -> Optional[pd.DataFrame]:
    """Filtre un DataFrame PCAET par code INSEE."""
    if df.empty:
        st.info(f"ℹ️ Aucune donnée PCAET trouvée pour la commune {code_insee}")
        return pd.DataFrame()
    
    # Chercher la colonne code INSEE
    insee_col = None
    for col in df.columns:
        if 'insee' in col.lower() or 'code commune' in col.lower():
            insee_col = col
            break
    
    if insee_col:
        filtered_df = df[df[insee_col].astype(str).str.strip() == code_insee]
        if not filtered_df.empty:
            st.success(f"✅ {len(filtered_df)} PCAET trouvé(s) pour la commune {code_insee}")
            return filtered_df
        else:
            st.info(f"ℹ️ Aucun PCAET trouvé pour la commune {code_insee}")
            return pd.DataFrame()
    
    st.warning(f"⚠️ Aucune colonne INSEE trouvée. Colonnes disponibles: {list(df.columns)}")
    return df


@st.cache_data(ttl=86400)  # Cache 24h
def charger_pcaet_v2_par_epci(code_epci: str) -> Optional[pd.DataFrame]:
    """
    Charge les données PCAET v2 pour un EPCI spécifique.
    
    Args:
        code_epci: Code SIREN de l'EPCI (ex: "200069785" pour Métropole de Lyon)
    
    Returns:
        DataFrame avec les données PCAET ou None si erreur
    """
    code_epci = str(code_epci).zfill(9)
    
    # Liste des URLs à essayer (par ordre de priorité)
    urls_to_try = [
        "https://www.data.gouv.fr/fr/datasets/r/ce0c5ed8-ac25-4f24-af28-ab8e92b44c09",  # URL directe CSV connue
        "https://www.data.gouv.fr/dataservices/pcaet-v2-demarches-partie-1-entete",  # URL du service
        "https://www.data.gouv.fr/fr/datasets/r/50070596-2c92-4758-a655-0f720079ac62",  # URL alternative
    ]
    
    for url in urls_to_try:
        try:
            with st.spinner(f"Téléchargement des données PCAET pour l'EPCI {code_epci}..."):
                response = requests.get(url, timeout=30)
                
                if response.status_code != 200:
                    continue
                
                # Vérifier si c'est du CSV
                if response.headers.get('Content-Type', '').startswith('text/csv') or url.endswith('.csv'):
                    try:
                        df = pd.read_csv(
                            url,
                            sep=";",
                            dtype=str,
                            encoding="utf-8",
                            on_bad_lines="warn"
                        )
                        # Filtrer par SIREN/EPCI
                        filtered_df = _filter_pcaet_by_epci(df, code_epci)
                        if filtered_df is not None:
                            return filtered_df
                    except Exception:
                        continue
                
                # Vérifier si c'est du JSON
                if response.headers.get('Content-Type', '').startswith('application/json'):
                    try:
                        # Vérifier que la réponse n'est pas vide
                        if not response.text.strip():
                            continue
                        data = response.json()
                        csv_url = None
                        
                        if isinstance(data, dict):
                            if 'resources' in data:
                                for resource in data['resources']:
                                    if resource.get('format', '').lower() == 'csv' and 'url' in resource:
                                        csv_url = resource['url']
                                        break
                            elif 'url' in data:
                                csv_url = data['url']
                        
                        if csv_url:
                            df = pd.read_csv(
                                csv_url,
                                sep=";",
                                dtype=str,
                                encoding="utf-8",
                                on_bad_lines="warn"
                            )
                            filtered_df = _filter_pcaet_by_epci(df, code_epci)
                            if filtered_df is not None:
                                return filtered_df
                    except Exception:
                        continue
                        
        except Exception:
            continue
    
    # Si toutes les URLs ont échoué
    st.error(f"❌ Impossible de télécharger les données PCAET v2. Toutes les URLs ont échoué.")
    return None


def _filter_pcaet_by_epci(df: pd.DataFrame, code_epci: str) -> Optional[pd.DataFrame]:
    """Filtre un DataFrame PCAET par code EPCI/SIREN."""
    if df.empty:
        st.info(f"ℹ️ Aucune donnée PCAET trouvée pour l'EPCI {code_epci}")
        return pd.DataFrame()
    
    # Chercher la colonne SIREN ou code EPCI
    siren_col = None
    for col in df.columns:
        if 'siren' in col.lower():
            siren_col = col
            break
    
    if siren_col:
        filtered_df = df[df[siren_col].astype(str).str.strip() == code_epci]
        if not filtered_df.empty:
            st.success(f"✅ {len(filtered_df)} PCAET trouvé(s) pour l'EPCI {code_epci}")
            return filtered_df
    
    # Si pas de colonne SIREN, essayer avec code EPCI
    epci_col = None
    for col in df.columns:
        if 'epci' in col.lower() and 'code' in col.lower():
            epci_col = col
            break
    
    if epci_col:
        filtered_df = df[df[epci_col].astype(str).str.strip() == code_epci]
        if not filtered_df.empty:
            st.success(f"✅ {len(filtered_df)} PCAET trouvé(s) pour l'EPCI {code_epci}")
            return filtered_df
    
    st.warning(f"⚠️ Aucune colonne SIREN/EPCI trouvée. Colonnes disponibles: {list(df.columns)}")
    return df


@st.cache_data(ttl=86400)  # Cache 24h
def charger_tous_pcaet_v2() -> Optional[pd.DataFrame]:
    """
    Charge TOUTES les données PCAET v2 sans filtrage.
    
    Attention: peut être volumineux et prendre du temps.
    
    Returns:
        DataFrame avec toutes les données PCAET
    """
    # Liste des URLs à essayer (par ordre de priorité)
    urls_to_try = [
        "https://www.data.gouv.fr/fr/datasets/r/ce0c5ed8-ac25-4f24-af28-ab8e92b44c09",  # URL directe CSV connue
        "https://www.data.gouv.fr/dataservices/pcaet-v2-demarches-partie-1-entete",  # URL du service
        "https://www.data.gouv.fr/fr/datasets/r/50070596-2c92-4758-a655-0f720079ac62",  # URL alternative
    ]
    
    for url in urls_to_try:
        try:
            with st.spinner("Téléchargement de toutes les données PCAET v2 (cela peut prendre quelques secondes)..."):
                response = requests.get(url, timeout=60)
                
                if response.status_code != 200:
                    continue
                
                # Vérifier si c'est du CSV
                if response.headers.get('Content-Type', '').startswith('text/csv') or url.endswith('.csv'):
                    try:
                        df = pd.read_csv(
                            url,
                            sep=";",
                            dtype=str,
                            encoding="utf-8",
                            on_bad_lines="warn"
                        )
                        st.success(f"✅ {len(df)} lignes téléchargées depuis {url}")
                        return df
                    except Exception:
                        continue
                
                # Vérifier si c'est du JSON
                if response.headers.get('Content-Type', '').startswith('application/json'):
                    try:
                        # Vérifier que la réponse n'est pas vide
                        if not response.text.strip():
                            continue
                        data = response.json()
                        csv_url = None
                        
                        if isinstance(data, dict):
                            if 'resources' in data:
                                for resource in data['resources']:
                                    if resource.get('format', '').lower() == 'csv' and 'url' in resource:
                                        csv_url = resource['url']
                                        break
                            elif 'url' in data:
                                csv_url = data['url']
                        
                        if csv_url:
                            df = pd.read_csv(
                                csv_url,
                                sep=";",
                                dtype=str,
                                encoding="utf-8",
                                on_bad_lines="warn"
                            )
                            st.success(f"✅ {len(df)} lignes téléchargées depuis {csv_url}")
                            return df
                    except Exception:
                        continue
                        
        except Exception:
            continue
    
    # Si toutes les URLs ont échoué
    st.error("❌ Impossible de télécharger les données PCAET v2. Toutes les URLs ont échoué.")
    return None


def afficher_pcaet_territoire(pcaet_df: pd.DataFrame, territoire_label: str) -> None:
    """
    Affiche les données PCAET pour un territoire dans un format Streamlit.
    
    Args:
        pcaet_df: DataFrame contenant les données PCAET
        territoire_label: Nom du territoire pour l'affichage
    """
    if pcaet_df is None or pcaet_df.empty:
        st.info(f"Aucune donnée PCAET disponible pour {territoire_label}")
        st.markdown(f"[Vérifier manuellement sur data.gouv.fr](https://www.data.gouv.fr/fr/datasets/pcaet-v2-demarches-partie-1-entete/)")
        return
    
    st.subheader(f"📋 PCAET pour {territoire_label}")
    
    # Sélectionner les colonnes pertinentes
    colonnes_utiles = [
        "Nom de la collectivité",
        "SIREN",
        "Type de PCAET",
        "Statut de la démarche",
        "Date de lancement",
        "Date d'approbation",
        "Date de dernière mise à jour",
        "Lien vers le PCAET",
        "Lien vers la délibération"
    ]
    
    # Garder seulement les colonnes qui existent
    colonnes_disponibles = [col for col in colonnes_utiles if col in pcaet_df.columns]
    
    # Ajouter toutes les autres colonnes qui pourraient être utiles
    autres_colonnes = [col for col in pcaet_df.columns if col not in colonnes_utiles]
    
    st.dataframe(
        pcaet_df[colonnes_disponibles + autres_colonnes],
        use_container_width=True,
        hide_index=True
    )
    
    # Statistiques
    if len(pcaet_df) > 0:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Nombre de PCAET", len(pcaet_df))
        
        with col2:
            if "Statut de la démarche" in pcaet_df.columns:
                statut_counts = pcaet_df["Statut de la démarche"].value_counts()
                if len(statut_counts) > 0:
                    st.metric("Statut principal", statut_counts.index[0])
        
        with col3:
            if "Date de dernière mise à jour" in pcaet_df.columns:
                last_update = pcaet_df["Date de dernière mise à jour"].max()
                st.metric("Dernière mise à jour", last_update if pd.notna(last_update) else "N/A")
    
    # Liens utiles
    st.markdown(f"[🔗 Voir tous les PCAET v2 sur data.gouv.fr](https://www.data.gouv.fr/fr/datasets/pcaet-v2-demarches-partie-1-entete/)")


# ============================================================================
# EXEMPLE D'INTÉGRATION DANS STREAMLIT
# ============================================================================

def exemple_integration_streamlit():
    """
    Exemple de comment intégrer ce script dans une app Streamlit.
    
    Copiez ce code dans votre app.py:
    
    # Importation
    from adev_pcaet_simple import (
        charger_pcaet_v2_par_commune,
        charger_pcaet_v2_par_epci,
        afficher_pcaet_territoire
    )
    
    # Dans votre code, après avoir obtenu communes_selectionnees:
    
    if communes_selectionnees:
        st.divider()
        st.markdown("# 🌍 Plans Climat-Air-Énergie Territorial (PCAET) v2")
        
        # Récupérer le code EPCI ou commune
        if type_territoire == "Commune":
            code_insee = communes_selectionnees[0]["code"]
            pcaet_data = charger_pcaet_v2_par_commune(code_insee)
        else:
            code_epci = communes_selectionnees[0]["codeEpci"]
            pcaet_data = charger_pcaet_v2_par_epci(code_epci)
        
        afficher_pcaet_territoire(pcaet_data, territoire_label)
    """
    pass


if __name__ == "__main__":
    # Test en mode standalone (sans Streamlit)
    print("=" * 80)
    print("Test du script PCAET v2 simplifié")
    print("=" * 80)
    
    # Test 1: Charger toutes les données
    print("\n1. Test: Charger toutes les données PCAET v2...")
    all_data = charger_tous_pcaet_v2()
    if all_data is not None:
        print(f"   → {len(all_data)} lignes téléchargées")
        print(f"   → Colonnes: {list(all_data.columns)[:5]}...")
    
    # Test 2: Filtrer par commune (Lyon)
    print("\n2. Test: Filtrer par commune (Lyon - 69001)...")
    lyon_data = charger_pcaet_v2_par_commune("69001")
    if lyon_data is not None:
        print(f"   → {len(lyon_data)} résultats")
        if not lyon_data.empty:
            print(f"   → Collectivités: {lyon_data['Nom de la collectivité'].unique().tolist()}")
    
    # Test 3: Filtrer par EPCI
    print("\n3. Test: Filtrer par EPCI (Métropole de Lyon - 200069785)...")
    epci_data = charger_pcaet_v2_par_epci("200069785")
    if epci_data is not None:
        print(f"   → {len(epci_data)} résultats")
        if not epci_data.empty:
            print(f"   → Collectivités: {epci_data['Nom de la collectivité'].unique().tolist()}")
    
    print("\n" + "=" * 80)
    print("Tests terminés. Intégrez ce script dans votre app Streamlit.")
    print("=" * 80)
