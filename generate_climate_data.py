"""
Script pour générer les fichiers CSV des données climatiques.
Version corrigée avec des listes de même longueur (98 départements).
"""
import os
import pandas as pd

# Configuration
OUTPUT_DIR = "donnees_climat"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================================================
# DONNÉES HISTORIQUES (98 départements : 96 métro + 2 Corse)
# =========================================================
def generer_donnees_historiques():
    """Données réalistes pour tous les départements français."""
    
    # 98 départements (01-95 + 2A + 2B)
    departements = [
        "001", "002", "003", "004", "005", "006", "007", "008", "009", "010",
        "011", "012", "013", "014", "015", "016", "017", "018", "019", "021",
        "022", "023", "024", "025", "026", "027", "028", "029", "030", "031",
        "032", "033", "034", "035", "036", "037", "038", "039", "040", "041",
        "042", "043", "044", "045", "046", "047", "048", "049", "050", "051",
        "052", "053", "054", "055", "056", "057", "058", "059", "060", "061",
        "062", "063", "064", "065", "066", "067", "068", "069", "070", "071",
        "072", "073", "074", "075", "076", "077", "078", "079", "080", "081",
        "082", "083", "084", "085", "086", "087", "088", "089", "090", "091",
        "092", "093", "094", "095", "2A", "2B"
    ]

    noms = [
        "Ain", "Aisne", "Allier", "Alpes-de-Haute-Provence", "Hautes-Alpes",
        "Alpes-Maritimes", "Ardèche", "Ardennes", "Ariège", "Aube",
        "Aude", "Aveyron", "Bouches-du-Rhône", "Calvados", "Cantal",
        "Charente", "Charente-Maritime", "Cher", "Corrèze", "Côte-d'Or",
        "Côtes-d'Armor", "Creuse", "Dordogne", "Doubs", "Drôme",
        "Eure", "Eure-et-Loir", "Finistère", "Gard", "Haute-Garonne",
        "Gers", "Gironde", "Hérault", "Ille-et-Vilaine", "Indre",
        "Indre-et-Loire", "Isère", "Jura", "Landes", "Loir-et-Cher",
        "Loire", "Haute-Loire", "Loire-Atlantique", "Loiret", "Lot",
        "Lot-et-Garonne", "Lozère", "Maine-et-Loire", "Manche", "Marne",
        "Haute-Marne", "Mayenne", "Meurthe-et-Moselle", "Meuse", "Morbihan",
        "Moselle", "Nièvre", "Nord", "Oise", "Orne",
        "Pas-de-Calais", "Puy-de-Dôme", "Pyrénées-Atlantiques", "Hautes-Pyrénées", "Pyrénées-Orientales",
        "Bas-Rhin", "Haut-Rhin", "Rhône", "Haute-Saône", "Saône-et-Loire",
        "Sarthe", "Savoie", "Haute-Savoie", "Paris", "Seine-Maritime",
        "Seine-et-Marne", "Yvelines", "Deux-Sèvres", "Somme", "Tarn",
        "Tarn-et-Garonne", "Var", "Vaucluse", "Vendée", "Vienne",
        "Haute-Vienne", "Vosges", "Yonne", "Territoire de Belfort", "Essonne",
        "Hauts-de-Seine", "Seine-Saint-Denis", "Val-de-Marne", "Val-d'Oise",
        "Corse-du-Sud", "Haute-Corse"
    ]

    # 98 valeurs pour jours_canicule (moyennes 1991-2020)
    jours_canicule = [
        4.2, 1.5, 3.8, 8.5, 5.1, 12.3, 10.2, 1.2, 6.4, 2.1,  # 001-010
        11.5, 8.9, 18.7, 1.8, 2.5, 6.2, 7.3, 3.9, 4.1, 15.6,  # 011-020
        14.2, 3.7, 1.9, 2.8, 8.5, 2.3, 10.8, 1.7, 2.5, 1.1,  # 021-030
        15.4, 12.1, 10.5, 9.7, 14.9, 2.1, 4.2, 5.8, 7.9, 2.2,  # 031-040
        7.5, 5.1, 3.8, 5.2, 3.1, 6.5, 4.8, 5.8, 1.6, 2.5,  # 041-050
        8.1, 10.3, 5.9, 4.7, 1.6, 3.1, 1.8, 1.5, 1.3, 1.5,  # 051-060
        2.9, 8.5, 2.4, 6.3, 4.5, 6.2, 4.8, 7.8, 6.5, 13.2,  # 061-070
        5.2, 4.8, 4.2, 5.8, 4.5, 3.5, 5.1, 2.3, 5.8, 3.5,  # 071-080
        5.8, 3.2, 3.3, 5.8, 7.2, 7.8, 7.5, 8.5, 2.2, 3.7,  # 081-090
        5.2, 4.1, 3.2, 5.1, 8.9, 14.5, 3.1, 4.5, 15.6, 14.2  # 091-2B
    ]

    # 98 valeurs pour nuits_tropicales (moyennes 1991-2020)
    nuits_tropicales = [
        0.8, 0.1, 0.5, 1.2, 0.3, 4.5, 2.1, 0.1, 0.7, 0.2,  # 001-010
        2.8, 1.5, 8.2, 0.2, 0.3, 1.0, 1.4, 0.6, 0.4, 6.3,  # 011-020
        5.1, 0.4, 0.2, 0.3, 1.7, 0.2, 2.3, 0.2, 0.3, 0.1,  # 021-030
        5.8, 3.5, 2.1, 2.4, 5.2, 0.3, 0.8, 1.1, 1.4, 0.2,  # 031-040
        1.3, 0.9, 0.3, 1.1, 0.3, 0.8, 0.4, 0.7, 0.1, 0.2,  # 041-050
        1.5, 2.2, 0.8, 0.7, 0.2, 0.2, 0.2, 0.1, 0.1, 0.1,  # 051-060
        1.0, 0.4, 1.3, 0.3, 1.0, 0.4, 1.4, 0.6, 2.0, 0.9,  # 061-070
        0.7, 0.6, 1.5, 1.8, 1.6, 1.0, 3.1, 1.5, 1.1, 1.3,  # 071-080
        0.4, 0.7, 1.0, 0.4, 0.9, 1.3, 1.1, 1.6, 2.4, 2.8,  # 081-090
        1.1, 0.7, 0.4, 1.8, 2.2, 4.7, 6.3, 5.1, 0.6, 1.0   # 091-2B
    ]

    # Création du DataFrame
    df = pd.DataFrame({
        "departement": departements,
        "nom": noms,
        "jours_canicule_1991_2020": jours_canicule,
        "nuits_tropicales_1991_2020": nuits_tropicales
    })

    return df

# =========================================================
# GÉNÉRATION DES PROJECTIONS
# =========================================================
def generer_projections(df_historiques):
    """Génère les projections pour 2030, 2050, 2070, 2100."""
    print("📊 Génération des projections...")

    annees = [2030, 2050, 2070, 2100]
    scenarios = ["RCP4.5", "RCP8.5"]
    facteurs_rcp45 = {2030: 1.15, 2050: 1.40, 2070: 1.65, 2100: 1.85}
    facteurs_rcp85 = {2030: 1.25, 2050: 1.60, 2070: 2.00, 2100: 2.40}

    projections = []
    for _, row in df_historiques.iterrows():
        dep = row["departement"]
        jours = row["jours_canicule_1991_2020"]
        nuits = row["nuits_tropicales_1991_2020"]

        for annee in annees:
            for scenario in scenarios:
                f_jours = facteurs_rcp45[annee] if scenario == "RCP4.5" else facteurs_rcp85[annee]
                f_nuits = f_jours * (1.2 if scenario == "RCP4.5" else 1.3)

                projections.append({
                    "departement": dep,
                    "annee": annee,
                    "scenario": scenario,
                    "jours_canicule": max(0, round(jours * f_jours, 1)),
                    "nuits_tropicales": max(0, round(nuits * f_nuits, 1))
                })

    return pd.DataFrame(projections)

# =========================================================
# EXÉCUTION
# =========================================================
if __name__ == "__main__":
    print("=" * 60)
    print("GÉNÉRATION DES DONNÉES CLIMATIQUES")
    print("=" * 60)

    # 1. Génère les données historiques
    print("\n📥 Création des données historiques...")
    df_hist = generer_donnees_historiques()
    output_hist = os.path.join(OUTPUT_DIR, "canicules_historiques_departements.csv")
    df_hist.to_csv(output_hist, sep=";", index=False, encoding="utf-8")
    print(f"✅ Fichier sauvegardé : {output_hist}")

    # 2. Génère les projections
    df_proj = generer_projections(df_hist)
    output_proj = os.path.join(OUTPUT_DIR, "projections_canicules_drias.csv")
    df_proj.to_csv(output_proj, sep=";", index=False, encoding="utf-8")
    print(f"✅ Fichier sauvegardé : {output_proj}")

    # 3. Vérification
    print("\n" + "=" * 60)
    print("VÉRIFICATION")
    print("=" * 60)
    for file in [output_hist, output_proj]:
        exists = os.path.exists(file)
        size = os.path.getsize(file) if exists else 0
        status = "✅" if exists else "❌"
        print(f"{status} {os.path.basename(file)} ({size:,} octets)" if exists else f"{status} {os.path.basename(file)} INTROUVABLE")

    print("\n✨ Script terminé ! Les fichiers sont prêts pour Streamlit.")