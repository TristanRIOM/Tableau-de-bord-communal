#!/usr/bin/env python3
"""
Script pour récupérer les données PCAET v2 de l'ADEME depuis data.gouv.fr
à partir d'un code commune (INSEE) ou d'un code EPCI (intercommunalité).

Dataset source: PCAET v2 - Démarches (Partie 1: En-tête)
URL: https://www.data.gouv.fr/fr/datasets/pcaet-v2-demarches-partie-1-entete/
API endpoint: https://www.data.gouv.fr/dataservices/pcaet-v2-demarches-partie-1-entete

Auteur: Tristan Riom
Date: 2026-07-27
"""

import requests
import pandas as pd
from typing import Optional, Union, List
import time
from pathlib import Path


class ADEMEPCAETDownloader:
    """
    Classe pour télécharger et filtrer les données PCAET v2 de l'ADEME.
    
    Les données contiennent des informations sur les Plans Climat-Air-Énergie Territorial
    des collectivités françaises, avec des métadonnées sur les démarches en cours.
    """
    
    # URL officielle du dataset PCAET v2 - Partie 1 (En-tête des démarches)
    DATASET_URL = "https://www.data.gouv.fr/dataservices/pcaet-v2-demarches-partie-1-entete"
    
    # URL alternative (direct CSV download)
    # Note: Cette URL peut changer, vérifier sur https://www.data.gouv.fr/fr/datasets/pcaet-v2-demarches-partie-1-entete/
    CSV_URL = "https://www.data.gouv.fr/fr/datasets/r/ce0c5ed8-ac25-4f24-af28-ab8e92b44c09"
    
    # Colonnes importantes pour le filtrage
    COMMUNE_COLUMNS = [
        "Code INSEE commune",
        "Nom commune",
        "SIREN EPCI",
        "Nom EPCI",
        "Code département",
        "Nom département"
    ]
    
    PCAET_COLUMNS = [
        "Nom de la collectivité",
        "SIREN",
        "Type de PCAET",
        "Statut de la démarche",
        "Date de lancement",
        "Date d'approbation",
        "Date de dernière mise à jour",
        "Lien vers le PCAET",
        "Lien vers la délibération",
        "Lien vers le bilan des émissions de GES",
        "Lien vers le plan d'actions",
        "Lien vers l'évaluation"
    ]
    
    def __init__(self, cache_dir: Optional[str] = None, cache_ttl: int = 86400):
        """
        Initialise le downloader.
        
        Args:
            cache_dir: Répertoire pour stocker le cache (None = pas de cache)
            cache_ttl: Durée de vie du cache en secondes (24h par défaut)
        """
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.cache_ttl = cache_ttl
        self._cached_df = None
        self._cache_time = 0
        
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _is_cache_valid(self) -> bool:
        """Vérifie si le cache est encore valide."""
        if self._cached_df is None:
            return False
        return (time.time() - self._cache_time) < self.cache_ttl
    
    def _load_from_cache(self) -> Optional[pd.DataFrame]:
        """Charge les données depuis le cache si disponible et valide."""
        if not self.cache_dir or not self._is_cache_valid():
            return None
        
        cache_file = self.cache_dir / "pcaet_v2_entete.csv"
        if cache_file.exists():
            try:
                return pd.read_csv(cache_file, sep=";", dtype=str, encoding="utf-8")
            except Exception as e:
                print(f"⚠️ Erreur de lecture du cache: {e}")
                return None
        return None
    
    def _save_to_cache(self, df: pd.DataFrame) -> None:
        """Sauvegarde les données en cache."""
        if not self.cache_dir:
            return
        
        cache_file = self.cache_dir / "pcaet_v2_entete.csv"
        try:
            df.to_csv(cache_file, sep=";", index=False, encoding="utf-8")
            self._cached_df = df
            self._cache_time = time.time()
        except Exception as e:
            print(f"⚠️ Erreur de sauvegarde du cache: {e}")
    
    def _download_dataset(self) -> pd.DataFrame:
        """
        Télécharge le dataset PCAET v2 depuis data.gouv.fr.
        
        Returns:
            DataFrame pandas contenant toutes les données
        """
        print("🔍 Tentative de téléchargement depuis l'API data.gouv.fr...")
        
        try:
            # Essayer l'URL directe du CSV
            response = requests.get(self.CSV_URL, timeout=30)
            response.raise_for_status()
            
            # Lire le CSV avec gestion des erreurs
            df = pd.read_csv(
                self.CSV_URL,
                sep=";",
                dtype=str,
                encoding="utf-8",
                on_bad_lines="warn",
                engine="python"
            )
            
            print(f"✅ Téléchargement réussi: {len(df)} lignes chargées")
            return df
            
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Erreur de téléchargement depuis {self.CSV_URL}: {e}")
            
            # Essayer l'URL alternative
            try:
                print("🔄 Tentative avec l'URL du service de données...")
                response = requests.get(self.DATASET_URL, timeout=30)
                response.raise_for_status()
                
                # Si c'est un CSV direct
                if response.headers.get('Content-Type', '').startswith('text/csv'):
                    df = pd.read_csv(
                        self.DATASET_URL,
                        sep=";",
                        dtype=str,
                        encoding="utf-8",
                        on_bad_lines="warn"
                    )
                    print(f"✅ Téléchargement réussi depuis {self.DATASET_URL}: {len(df)} lignes")
                    return df
                else:
                    # Sinon, essayer de parser comme JSON pour trouver l'URL du CSV
                    data = response.json()
                    if isinstance(data, dict) and 'resources' in data:
                        csv_resource = next(
                            (r for r in data['resources'] 
                             if r.get('format', '').lower() == 'csv'),
                            None
                        )
                        if csv_resource and 'url' in csv_resource:
                            csv_url = csv_resource['url']
                            print(f"📍 URL CSV trouvée: {csv_url}")
                            df = pd.read_csv(
                                csv_url,
                                sep=";",
                                dtype=str,
                                encoding="utf-8",
                                on_bad_lines="warn"
                            )
                            print(f"✅ Téléchargement réussi depuis {csv_url}: {len(df)} lignes")
                            return df
                    
            except Exception as e2:
                print(f"❌ Erreur avec toutes les URLs: {e2}")
        
        except Exception as e:
            print(f"❌ Erreur inattendue: {e}")
        
        # Retourner un DataFrame vide si tout échoue
        print("⚠️ Impossible de télécharger les données. Retourne un DataFrame vide.")
        return pd.DataFrame()
    
    def get_all_data(self, force_refresh: bool = False) -> pd.DataFrame:
        """
        Récupère toutes les données PCAET v2.
        
        Args:
            force_refresh: Force le téléchargement même si le cache est valide
        
        Returns:
            DataFrame contenant toutes les données PCAET
        """
        # Vérifier le cache
        if not force_refresh:
            cached_df = self._load_from_cache()
            if cached_df is not None:
                print(f"📋 Données chargées depuis le cache ({len(cached_df)} lignes)")
                return cached_df
        
        # Télécharger les données
        df = self._download_dataset()
        
        if df.empty:
            print("⚠️ Aucune donnée téléchargée. Vérifiez votre connexion internet.")
            return df
        
        # Sauvegarder en cache
        self._save_to_cache(df)
        
        return df
    
    def filter_by_commune(self, 
                         code_insee: Union[str, int], 
                         all_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Filtre les données PCAET par code INSEE de la commune.
        
        Args:
            code_insee: Code INSEE de la commune (ex: "69001" pour Lyon)
            all_data: DataFrame contenant les données (si déjà chargées)
        
        Returns:
            DataFrame filtré contenant les PCAET pour cette commune
        """
        code_insee = str(code_insee).zfill(5)  # Normaliser au format 5 chiffres
        
        if all_data is None:
            all_data = self.get_all_data()
        
        if all_data.empty:
            return pd.DataFrame()
        
        # Chercher dans les colonnes possibles
        insee_columns = [col for col in all_data.columns 
                        if 'insee' in col.lower() or 'code commune' in col.lower()]
        
        if not insee_columns:
            print(f"⚠️ Aucune colonne de code INSEE trouvée dans les données. Colonnes disponibles: {list(all_data.columns)}")
            return pd.DataFrame()
        
        # Filtrer par code INSEE
        for col in insee_columns:
            if col in all_data.columns:
                filtered = all_data[all_data[col].astype(str).str.strip() == code_insee]
                if not filtered.empty:
                    print(f"✅ Trouvé {len(filtered)} PCAET pour la commune {code_insee}")
                    return filtered
        
        print(f"⚠️ Aucun PCAET trouvé pour la commune {code_insee}")
        return pd.DataFrame()
    
    def filter_by_epci(self, 
                      code_epci: Union[str, int], 
                      all_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Filtre les données PCAET par code SIREN de l'EPCI (intercommunalité).
        
        Args:
            code_epci: Code SIREN de l'EPCI (ex: "200069785" pour Métropole de Lyon)
            all_data: DataFrame contenant les données (si déjà chargées)
        
        Returns:
            DataFrame filtré contenant les PCAET pour cet EPCI
        """
        code_epci = str(code_epci).zfill(9)  # Normaliser au format SIREN (9 chiffres)
        
        if all_data is None:
            all_data = self.get_all_data()
        
        if all_data.empty:
            return pd.DataFrame()
        
        # Chercher dans les colonnes SIREN
        siren_columns = [col for col in all_data.columns 
                        if 'siren' in col.lower() or 'epci' in col.lower()]
        
        if not siren_columns:
            print(f"⚠️ Aucune colonne SIREN/EPCI trouvée. Colonnes disponibles: {list(all_data.columns)}")
            return pd.DataFrame()
        
        # Filtrer par SIREN
        for col in siren_columns:
            if col in all_data.columns:
                filtered = all_data[all_data[col].astype(str).str.strip() == code_epci]
                if not filtered.empty:
                    print(f"✅ Trouvé {len(filtered)} PCAET pour l'EPCI {code_epci}")
                    return filtered
        
        print(f"⚠️ Aucun PCAET trouvé pour l'EPCI {code_epci}")
        return pd.DataFrame()
    
    def get_pcaet_for_territory(self, 
                               codes_communes: Optional[List[Union[str, int]]] = None,
                               code_epci: Optional[Union[str, int]] = None) -> pd.DataFrame:
        """
        Récupère les données PCAET pour un territoire (commune ou EPCI).
        
        Args:
            codes_communes: Liste de codes INSEE des communes
            code_epci: Code SIREN de l'EPCI
        
        Returns:
            DataFrame contenant les PCAET pour le territoire
        """
        all_data = self.get_all_data()
        
        if all_data.empty:
            return pd.DataFrame()
        
        results = []
        
        # Filtrer par communes
        if codes_communes:
            for code in codes_communes:
                result = self.filter_by_commune(code, all_data)
                results.append(result)
        
        # Filtrer par EPCI
        if code_epci:
            result = self.filter_by_epci(code_epci, all_data)
            results.append(result)
        
        if results:
            combined = pd.concat(results, ignore_index=True)
            # Supprimer les doublons
            combined = combined.drop_duplicates()
            print(f"✅ Total: {len(combined)} PCAET trouvés pour le territoire")
            return combined
        
        return pd.DataFrame()
    
    def get_summary(self, 
                   codes_communes: Optional[List[Union[str, int]]] = None,
                   code_epci: Optional[Union[str, int]] = None) -> dict:
        """
        Retourne un résumé des données PCAET pour un territoire.
        
        Args:
            codes_communes: Liste de codes INSEE des communes
            code_epci: Code SIREN de l'EPCI
        
        Returns:
            Dictionnaire avec les statistiques clés
        """
        pcaet_data = self.get_pcaet_for_territory(codes_communes, code_epci)
        
        if pcaet_data.empty:
            return {
                "total_pcaet": 0,
                "collectivites": [],
                "statut_distribution": {},
                "derniere_maj": None,
                "liens": []
            }
        
        # Statistiques de base
        total = len(pcaet_data)
        
        # Collectivités
        collectivites = pcaet_data["Nom de la collectivité"].unique().tolist() if "Nom de la collectivité" in pcaet_data.columns else []
        
        # Distribution par statut
        if "Statut de la démarche" in pcaet_data.columns:
            statut_dist = pcaet_data["Statut de la démarche"].value_counts().to_dict()
        else:
            statut_dist = {}
        
        # Date de dernière mise à jour
        if "Date de dernière mise à jour" in pcaet_data.columns:
            dernieres_maj = pcaet_data["Date de dernière mise à jour"].dropna()
            if not dernieres_maj.empty:
                dernière_maj = dernieres_maj.max()
            else:
                dernière_maj = None
        else:
            dernière_maj = None
        
        # Lien vers les PCAET
        liens = []
        if "Lien vers le PCAET" in pcaet_data.columns:
            liens = pcaet_data["Lien vers le PCAET"].dropna().unique().tolist()
        
        return {
            "total_pcaet": total,
            "collectivites": collectivites,
            "statut_distribution": statut_dist,
            "derniere_maj": dernière_maj,
            "liens": liens,
            "details": pcaet_data.to_dict('records') if total <= 10 else "Trop de résultats pour afficher les détails"
        }


# ============================================================================
# FONCTIONS SIMPLES (pour une utilisation directe sans classe)
# ============================================================================

def telecharger_pcaet_v2(code_territoire: str, 
                        territoire_type: str = "commune",
                        cache_ttl: int = 86400) -> pd.DataFrame:
    """
    Fonction simple pour télécharger les données PCAET v2 pour une commune ou un EPCI.
    
    Args:
        code_territoire: Code INSEE (5 chiffres) pour une commune, ou SIREN (9 chiffres) pour un EPCI
        territoire_type: "commune" ou "epci"
        cache_ttl: Durée de vie du cache en secondes
    
    Returns:
        DataFrame avec les données PCAET
    
    Exemple:
        >>> # Pour la commune de Lyon (69001)
        >>> df = telecharger_pcaet_v2("69001", "commune")
        >>> 
        >>> # Pour la Métropole de Lyon (200069785)
        >>> df = telecharger_pcaet_v2("200069785", "epci")
    """
    downloader = ADEMEPCAETDownloader(cache_ttl=cache_ttl)
    
    if territoire_type == "commune":
        return downloader.filter_by_commune(code_territoire)
    elif territoire_type == "epci":
        return downloader.filter_by_epci(code_territoire)
    else:
        raise ValueError("territoire_type doit être 'commune' ou 'epci'")


def get_pcaet_summary(code_territoire: str, 
                     territoire_type: str = "commune") -> dict:
    """
    Retourne un résumé des données PCAET pour un territoire.
    
    Args:
        code_territoire: Code INSEE ou SIREN
        territoire_type: "commune" ou "epci"
    
    Returns:
        Dictionnaire avec les statistiques
    """
    downloader = ADEMEPCAETDownloader()
    
    if territoire_type == "commune":
        return downloader.get_summary(codes_communes=[code_territoire])
    else:
        return downloader.get_summary(code_epci=code_territoire)


# ============================================================================
# EXEMPLE D'UTILISATION
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("ADEME PCAET v2 Data Downloader")
    print("=" * 80)
    print()
    
    # Créer un instance du downloader
    downloader = ADEMEPCAETDownloader(cache_dir="./cache_pcaet", cache_ttl=3600)
    
    # Exemple 1: Récupérer toutes les données
    print("1. Téléchargement de toutes les données PCAET v2...")
    all_data = downloader.get_all_data()
    print(f"   → {len(all_data)} lignes téléchargées")
    print(f"   Colonnes disponibles: {list(all_data.columns)[:10]}...")
    print()
    
    # Exemple 2: Filtrer par commune (Lyon)
    print("2. Recherche des PCAET pour la commune de Lyon (69001)...")
    lyon_data = downloader.filter_by_commune("69001")
    if not lyon_data.empty:
        print(f"   → {len(lyon_data)} PCAET trouvés")
        print(lyon_data[[
            "Nom de la collectivité", 
            "Type de PCAET", 
            "Statut de la démarche",
            "Date d'approbation"
        ]].head())
    else:
        print("   → Aucun PCAET trouvé pour Lyon")
    print()
    
    # Exemple 3: Filtrer par EPCI (Métropole de Lyon)
    print("3. Recherche des PCAET pour la Métropole de Lyon (200069785)...")
    metro_data = downloader.filter_by_epci("200069785")
    if not metro_data.empty:
        print(f"   → {len(metro_data)} PCAET trouvés")
        print(metro_data[[
            "Nom de la collectivité",
            "Type de PCAET",
            "Statut de la démarche"
        ]].head())
    else:
        print("   → Aucun PCAET trouvé pour la Métropole de Lyon")
    print()
    
    # Exemple 4: Résumé pour un territoire
    print("4. Résumé pour la commune de Paris (75000)...")
    summary = downloader.get_summary(codes_communes=["75000"])
    print(f"   Total PCAET: {summary['total_pcaet']}")
    print(f"   Collectivités: {summary['collectivites']}")
    print(f"   Distribution par statut: {summary['statut_distribution']}")
    print()
    
    print("=" * 80)
    print("Exemples terminés. Utilisez la classe ADEMEPCAETDownloader dans votre code.")
    print("=" * 80)
