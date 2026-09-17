"""
Etape 3 : construction des series et detection des ruptures candidates.

Les seuils sont des parametres du module, fixes avant execution et versionnes
avec le code. Toute modification ulterieure se documente comme une revision de
la regle, jamais comme un ajustement silencieux apres coup.

La detection ne prouve rien. Elle produit une liste de candidates a verifier
une par une contre la methode d'estimation, les commentaires de l'exploitant,
les seuils de declaration et le perimetre d'installation.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import inrp

REGLE = Path("data/regle_detection.json")

# --- Parametres de la regle, fixes d'avance ---------------------------------

FENETRE = 3       # annees comparees de part et d'autre du point teste
FACTEUR = 2.0     # ecart de niveau retenu comme candidat, a la hausse ou a la baisse
PLANCHER_KG = 100.0  # niveau median minimal, en dessous le bruit domine
ABSENCE_MIN = 2   # annees consecutives sans declaration valant arret de declaration

JUSTIFICATION = (
    "Fenetre de 3 ans de part et d'autre : c'est le minimum permettant de "
    "distinguer un changement de niveau persistant d'une annee atypique, tout "
    "en laissant une plage de detection de 2013 a 2021 sur la serie 2010-2024. "
    "Facteur 2 : les variations annuelles de production induisent couramment "
    "des ecarts de 20 a 50 pour cent, un doublement ou une division par deux du "
    "niveau median est rare sans cause identifiable. Plancher de 100 kg : en "
    "dessous, une variation d'un facteur 2 represente une masse trop faible "
    "pour etre distinguee du bruit de declaration et du seuil d'agregation "
    "sous une tonne."
)


def ecrire_regle() -> dict:
    """Archive la regle de detection avant de l'appliquer."""
    d = {
        "fenetre_annees": FENETRE,
        "facteur_rupture": FACTEUR,
        "plancher_kg": PLANCHER_KG,
        "absence_min_annees": ABSENCE_MIN,
        "serie_de_base": "rejets, tous milieux confondus, par installation et par metal",
        "justification": JUSTIFICATION,
        "fixee_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    REGLE.parent.mkdir(parents=True, exist_ok=True)
    REGLE.write_text(json.dumps(d, indent=2, ensure_ascii=False))
    return d


# --- Construction des series ------------------------------------------------


def series(D: pd.DataFrame, ids: list[int], flux: str = "rejets") -> pd.DataFrame:
    """Grille complete installation x metal x annee, en kg.

    Une case vide signifie absence de declaration, ce qui n'est pas un zero.
    Les deux sont distingues : NaN pour l'absence, 0.0 pour un zero declare.
    """
    d = D[(D["flux"] == flux) & (D["id"].isin(ids))]
    s = d.groupby(["id", "metal", "annee"])["kg"].sum()
    annees = range(inrp.ANNEES[0], inrp.ANNEES[1] + 1)
    idx = pd.MultiIndex.from_product(
        [sorted(set(d["id"])), sorted(set(d["metal"])), annees],
        names=["id", "metal", "annee"],
    )
    return s.reindex(idx).reset_index()


def methode_dominante(D: pd.DataFrame, flux: str = "rejets") -> pd.DataFrame:
    """Methode d'estimation portant la plus grande masse, par couple et par an."""
    d = D[D["flux"] == flux]
    g = d.groupby(["id", "metal", "annee", "methode"])["kg"].sum().reset_index()
    return (
        g.sort_values("kg")
        .drop_duplicates(["id", "metal", "annee"], keep="last")
        .rename(columns={"methode": "methode_dominante"})
        [["id", "metal", "annee", "methode_dominante"]]
    )


# --- Detection --------------------------------------------------------------


def candidates(S: pd.DataFrame) -> pd.DataFrame:
    """Ruptures de niveau candidates, selon la regle fixee ci-dessus.

    Pour chaque annee t testable, compare la mediane des FENETRE annees
    precedentes, t inclus exclu, a celle des FENETRE annees suivantes, t inclus.
    """
    out = []
    for (i, m), g in S.groupby(["id", "metal"]):
        g = g.sort_values("annee").reset_index(drop=True)
        v = g["kg"].to_numpy(dtype=float)
        a = g["annee"].to_numpy()
        for k in range(FENETRE, len(v) - FENETRE + 1):
            av, ap = v[k - FENETRE:k], v[k:k + FENETRE]
            if np.isnan(av).all() or np.isnan(ap).all():
                continue
            m_av, m_ap = np.nanmedian(av), np.nanmedian(ap)
            if max(m_av, m_ap) < PLANCHER_KG:
                continue
            if m_av <= 0:
                continue
            ratio = m_ap / m_av
            if ratio >= FACTEUR or ratio <= 1 / FACTEUR:
                out.append(
                    {
                        "id": i,
                        "metal": m,
                        "annee_rupture": int(a[k]),
                        "median_avant_kg": round(m_av, 1),
                        "median_apres_kg": round(m_ap, 1),
                        "ratio": round(ratio, 3),
                        "sens": "hausse" if ratio >= FACTEUR else "baisse",
                    }
                )
    c = pd.DataFrame(out)
    if c.empty:
        return c
    # Une meme rupture peut declencher sur plusieurs annees voisines.
    # On garde l'annee au ratio le plus extreme par episode contigu.
    c = c.sort_values(["id", "metal", "annee_rupture"])
    c["ecart"] = np.maximum(c["ratio"], 1 / c["ratio"])
    c["episode"] = (
        c.groupby(["id", "metal"])["annee_rupture"].diff().fillna(99).gt(1).cumsum()
    )
    return (
        c.sort_values("ecart")
        .drop_duplicates(["id", "metal", "episode"], keep="last")
        .sort_values(["id", "metal", "annee_rupture"])
        .drop(columns=["ecart", "episode"])
        .reset_index(drop=True)
    )


def arrets_declaration(S: pd.DataFrame) -> pd.DataFrame:
    """Couples declares puis absents pendant au moins ABSENCE_MIN annees."""
    out = []
    for (i, m), g in S.groupby(["id", "metal"]):
        g = g.sort_values("annee")
        v, a = g["kg"].to_numpy(dtype=float), g["annee"].to_numpy()
        presents = np.where(~np.isnan(v))[0]
        if len(presents) == 0:
            continue
        dernier = presents[-1]
        manquants = len(v) - 1 - dernier
        if manquants >= ABSENCE_MIN and np.nanmedian(v[presents][-3:]) >= PLANCHER_KG:
            out.append(
                {
                    "id": i,
                    "metal": m,
                    "derniere_annee_declaree": int(a[dernier]),
                    "annees_sans_declaration": int(manquants),
                    "niveau_final_kg": round(float(np.nanmedian(v[presents][-3:])), 1),
                }
            )
    return pd.DataFrame(out)


def annoter(c: pd.DataFrame, meth: pd.DataFrame, noms: pd.Series) -> pd.DataFrame:
    """Ajoute le nom de l'installation et le changement de methode a la rupture."""
    if c.empty:
        return c
    c = c.copy()
    c["installation"] = c["id"].map(noms)
    m = meth.set_index(["id", "metal", "annee"])["methode_dominante"]
    c["methode_avant"] = [
        m.get((r.id, r.metal, r.annee_rupture - 1)) for r in c.itertuples()
    ]
    c["methode_apres"] = [
        m.get((r.id, r.metal, r.annee_rupture)) for r in c.itertuples()
    ]
    c["methode_changee"] = (
        c["methode_avant"].notna()
        & c["methode_apres"].notna()
        & (c["methode_avant"] != c["methode_apres"])
    )
    return c
