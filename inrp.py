"""
Projet de contre-expertise INRP, module d'ingestion et de selection.

Version 2, corrigee apres lecture des fichiers reels. Trois corrections par
rapport a la version 1 :
  1. Les metaux n'ont pas de numero CAS dans l'INRP, ils portent des codes
     de la forme "NA - 08". Le dictionnaire de la v1 ne trouvait rien.
  2. Toute agregation se fait sur NPRI_ID. Le nom d'installation change de
     graphie selon les annees et scinde les series si on l'utilise comme cle.
  3. La serie de base est le total des rejets tous milieux confondus, a cause
     du groupe de declaration agrege "<1tonne" qui fait disparaitre les
     rejets a l'air d'une installation passant sous le seuil.

La selection des installations est figee par une regle ecrite, appliquee sur
la fenetre de reference uniquement, et archivee avant toute analyse temporelle.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATA = Path("data/brut")
SORTIES = Path("data/derive")
MANIFESTE = Path("data/manifeste_sources.json")
SELECTION = Path("data/selection_figee.json")

FICHIERS = {
    "rejets": "NPRI-INRP_ReleasesRejets_1993-present.csv",
    "eliminations": "NPRI-INRP_DisposalsEliminations_1993-present.csv",
    "transferts": "NPRI-INRP_DisposalsEliminations_TransfersTransferts_1993-present.csv",
    "geo": "NPRI-INRP_GeolocationsGeolocalisation_1993-present.csv",
    "commentaires": "NPRI-INRP_CommentsCommentaires_1997-present.csv",
}

ENCODAGE = "cp1252"  # verifie sur les cinq fichiers

ORIGINE = (45.6166, -72.9569)  # Saint-Hyacinthe
RAYON_KM = 50.0
ANNEES = (2010, 2024)
REFERENCE = (2010, 2012)  # fenetre servant a figer la selection

# Regle de selection, enoncee ici pour etre citable dans le rapport :
# installations de la premiere transformation des metaux (SCIAN 331), situees
# dans le rayon, classees par masse totale de metaux rejetee sur la fenetre de
# reference, les cinq premieres retenues.
PREFIXE_SCIAN = "331"
N_RETENUES = 5

# Metaux et leurs composes. Codes INRP, pas des numeros CAS.
METAUX = {
    "NA - 02": "arsenic",
    "NA - 03": "cadmium",
    "NA - 04": "chrome",
    "NA - 06": "cuivre",
    "NA - 08": "plomb",
    "NA - 09": "manganese",
    "NA - 10": "mercure",
    "NA - 11": "nickel",
    "NA - 14": "zinc",
}
# Tenus hors du total pour eviter le double comptage :
#   NA - 19   chrome hexavalent, deja compris dans le chrome total
#   7440-66-6 zinc fumee ou poussiere, entree distincte du zinc et composes
EXCLUS_DU_TOTAL = {"NA - 19", "7440-66-6"}

# Groupes de rejets. Le quatrieme est un total agrege declare par les
# installations sous le seuil d'une tonne, sans ventilation par milieu.
GROUPE_AGREGE = "Total des rejets dans tous les milieux (<1tonne)"

# Categories d'elimination a isoler, leurs masses ecrasent tout le reste.
ELIMINATION_MINIERE = {"Gestion des résidus miniers", "Gestion des stériles"}

VERS_KG = {"tonnes": 1000.0, "kg": 1.0, "grams": 0.001}
UNITES_NON_MASSE = {"g TEQ"}  # dioxines et furanes, hors famille metaux

COL = {  # noms reels des colonnes, verifies sur les fichiers
    "annee": "Reporting_Year / Année",
    "id": "NPRI_ID / No_INRP",
    "entreprise": "Company_Name / Dénomination_sociale_de_l'entreprise",
    "installation": "Facility_Name / Installation",
    "scian": "NAICS / Code_SCIAN",
    "cas": "CAS_Number / No_CAS",
    "substance": "Substance Name (French) / Nom de substance (Français)",
    "groupe": "Group (French) / Groupe (Français)",
    "categorie": "Category (French) / Catégorie (Français)",
    "quantite": "Quantity / Quantité",
    "unite": "Units / Unités",
    "methode": "Estimation_Method / Méthode_d’estimation",
}
COL_GEO = {
    "id": "NPRI ID / ID INRP",
    "lat": "Latitude / Latitude",
    "lon": "Longitude / Longitude",
    "ville": "City / Ville",
    "scian": "NAICS / Code SCIAN",
    "entreprise": "Company Name / Raison Sociale",
    "installation": "Facility Name / Nom de l'installation",
}


# ---------------------------------------------------------------------------
# Archivage des sources
# ---------------------------------------------------------------------------


def _sha256(chemin: Path) -> str:
    h = hashlib.sha256()
    with chemin.open("rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def manifeste_local() -> dict:
    """Empreinte et horodatage des fichiers presents. A lancer une seule fois."""
    entrees = {}
    for cle, nom in FICHIERS.items():
        chemin = DATA / nom
        if chemin.exists():
            entrees[cle] = {
                "fichier": nom,
                "octets": chemin.stat().st_size,
                "sha256": _sha256(chemin),
                "archive_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
    MANIFESTE.parent.mkdir(parents=True, exist_ok=True)
    MANIFESTE.write_text(
        json.dumps(entrees, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return entrees


def verifier_manifeste() -> dict:
    """A lancer au debut de chaque session. MODIFIE invalide tout resultat."""
    ref = json.loads(MANIFESTE.read_text(encoding="utf-8"))
    return {
        cle: (
            "absent"
            if not (DATA / e["fichier"]).exists()
            else "identique"
            if _sha256(DATA / e["fichier"]) == e["sha256"]
            else "MODIFIE"
        )
        for cle, e in ref.items()
    }
    


# ---------------------------------------------------------------------------
# Chargement
# ---------------------------------------------------------------------------


def _en_kg(quantites: pd.Series, unites: pd.Series) -> pd.Series:
    inconnues = sorted(set(unites.dropna()) - set(VERS_KG) - UNITES_NON_MASSE)
    if inconnues:
        print(f"  unites non converties, mises a NaN : {inconnues}")
    return pd.to_numeric(quantites, errors="coerce") * unites.map(VERS_KG)


def installations_dans_rayon(rayon_km: float = RAYON_KM) -> pd.DataFrame:
    """Installations declarantes dans le rayon, distance orthodromique."""
    g = pd.read_csv(DATA / FICHIERS["geo"], encoding=ENCODAGE, low_memory=False)
    g = g.dropna(subset=[COL_GEO["lat"], COL_GEO["lon"]]).copy()
    lat = np.radians(pd.to_numeric(g[COL_GEO["lat"]], errors="coerce"))
    lon = np.radians(pd.to_numeric(g[COL_GEO["lon"]], errors="coerce"))
    lat0, lon0 = np.radians(ORIGINE[0]), np.radians(ORIGINE[1])
    a = (
        np.sin((lat - lat0) / 2) ** 2
        + np.cos(lat0) * np.cos(lat) * np.sin((lon - lon0) / 2) ** 2
    )
    g["distance_km"] = 2 * 6371.0088 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
    proches = g[g["distance_km"] <= rayon_km]
    return proches.sort_values("distance_km").drop_duplicates(subset=[COL_GEO["id"]])


def charger_metaux(ids: set[int] | None = None) -> pd.DataFrame:
    """Les trois flux, metaux seuls, en kilogrammes, empiles et etiquetes.

    Les flux ne sont jamais additionnes entre eux ici. La colonne 'flux' est
    conservee pour que toute somme ulterieure soit un choix explicite.
    """
    usecols = [
        COL[k]
        for k in ("annee", "id", "entreprise", "installation", "scian", "cas",
                  "substance", "groupe", "categorie", "quantite", "unite", "methode")
    ]
    morceaux = []
    for flux in ("rejets", "eliminations", "transferts"):
        print(f"lecture {flux}")
        d = pd.read_csv(
            DATA / FICHIERS[flux], encoding=ENCODAGE, low_memory=False, usecols=usecols
        )
        d = d[d[COL["cas"]].isin(METAUX)]
        if ids is not None:
            d = d[d[COL["id"]].isin(ids)]
        d = d.rename(columns={v: k for k, v in COL.items()}).copy()
        d["kg"] = _en_kg(d["quantite"], d["unite"])
        d["metal"] = d["cas"].map(METAUX)
        d["flux"] = flux
        morceaux.append(d)
    D = pd.concat(morceaux, ignore_index=True)
    D = D[D["annee"].between(*ANNEES)]
    # Nom d'affichage stable, la graphie varie selon l'annee de declaration.
    dernier = D.sort_values("annee").groupby("id")[["installation", "entreprise"]].last()
    D["nom"] = D["id"].map(dernier["installation"])
    D["societe"] = D["id"].map(dernier["entreprise"])
    D["agrege_sous_1t"] = D["groupe"].eq(GROUPE_AGREGE)
    D["elimination_miniere"] = D["categorie"].isin(ELIMINATION_MINIERE)
    return D


# ---------------------------------------------------------------------------
# Selection figee
# ---------------------------------------------------------------------------


def figer_selection(D: pd.DataFrame, proches: pd.DataFrame) -> dict:
    """Applique la regle de selection et archive son resultat.

    La regle n'utilise que la fenetre de reference. Aucune donnee posterieure
    a REFERENCE[1] n'intervient dans le choix. Le fichier produit est
    horodate et doit etre versionne avant toute analyse temporelle.
    """
    scian = proches.set_index(COL_GEO["id"])[COL_GEO["scian"]].astype(str)
    ref = D[(D["annee"].between(*REFERENCE)) & (D["flux"] == "rejets")]
    classement = ref.groupby("id")["kg"].sum().sort_values(ascending=False)
    classement = classement[
        classement.index.map(lambda i: scian.get(i, "").startswith(PREFIXE_SCIAN))
    ]
    retenues = classement.head(N_RETENUES)

    noms = D.drop_duplicates("id").set_index("id")["nom"]
    resultat = {
        "regle": (
            f"Installations de SCIAN commencant par {PREFIXE_SCIAN}, situees a "
            f"moins de {RAYON_KM} km de {ORIGINE}, classees par masse totale de "
            f"metaux rejetee sur {REFERENCE[0]}-{REFERENCE[1]}, "
            f"{N_RETENUES} premieres retenues."
        ),
        "fige_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "retenues": [
            {
                "npri_id": int(i),
                "nom": noms.get(i),
                "scian": scian.get(i),
                "rejets_kg_reference": round(float(v), 1),
                "distance_km": round(
                    float(proches.set_index(COL_GEO["id"]).loc[i, "distance_km"]), 1
                ),
            }
            for i, v in retenues.items()
        ],
        "ecartees_rang_suivant": [
            {"npri_id": int(i), "nom": noms.get(i), "rejets_kg_reference": round(float(v), 1)}
            for i, v in classement.iloc[N_RETENUES:N_RETENUES + 3].items()
        ],
    }
    SELECTION.parent.mkdir(parents=True, exist_ok=True)
    SELECTION.write_text(
        json.dumps(resultat, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return resultat

def charger_commentaires(ids=None):
    """Commentaires des exploitants. Encodage distinct des autres fichiers."""
    C = pd.read_csv(
        DATA / FICHIERS["commentaires"], encoding="latin-1", low_memory=False
    )
    C = C.rename(
        columns={
            COL["annee"]: "annee",
            COL["id"]: "id",
            COL["substance"]: "substance",
            "Comment_Type_Name (French) Type_de_commentaire (Français)": "type",
            "Comment / Commentaires": "commentaire",
        }
    )
    if ids is not None:
        C = C[C["id"].isin(ids)]
    return C[["annee", "id", "substance", "type", "commentaire"]]