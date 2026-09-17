"""
Outil de triage d'une rupture candidate.

    python verifie.py <npri_id> <metal> <annee>

Affiche, dans l'ordre de verification fixe par le protocole du projet, les
elements factuels necessaires au triage d'une candidate. L'outil n'interprete
rien et ne conclut rien : il rassemble les faits, la lecture est consignee a
la main dans analyse/triage.md.

Ordre des blocs, identique a la grille de triage :
  1. ventilation par flux
  2. groupe de declaration
  3. categorie de rejet
  4. code de methode d'estimation, sur les fenetres de trois ans
  5. commentaires de l'exploitant, plus ou moins deux ans
  6. installations liees du meme exploitant

Le bloc 0 rappelle le contexte de declaration de l'installation, qui sert a
tester l'hypothese d'un passage sous le seuil de declaration.
"""

import sys

import pandas as pd

import inrp
import detection as det

pd.set_option("display.width", 220)
pd.set_option("display.max_rows", 200)
pd.set_option("display.max_colwidth", 200)

if len(sys.argv) != 4:
    sys.exit("usage: python verifie.py <npri_id> <metal> <annee>")

npri_id = int(sys.argv[1])
metal = sys.argv[2]
annee = int(sys.argv[3])

if metal not in inrp.CODE_PAR_METAL:
    sys.exit(f"metal inconnu : {metal!r}. Attendu parmi {sorted(inrp.CODE_PAR_METAL)}.")
code = inrp.CODE_PAR_METAL[metal]

FEN = det.FENETRE
AV = range(annee - FEN, annee)
AP = range(annee, annee + FEN)


def _fenetre(a: int) -> str:
    if a in AV:
        return "avant"
    if a in AP:
        return "apres"
    return ""


D = inrp.charger_metaux()
d = D[(D["id"] == npri_id) & (D["metal"] == metal)]
if d.empty:
    sys.exit(f"aucune ligne pour l'installation {npri_id} et le metal {metal}.")

nom = d["nom"].iloc[0]
societe = d["societe"].iloc[0]

print(f"CANDIDATE  {npri_id}  {nom}")
print(f"           exploitant declare : {societe}")
print(f"           metal : {metal}, code INRP {code}")
print(f"           annee testee : {annee}")
print(f"           fenetre avant : {AV.start} a {AV.stop - 1}")
print(f"           fenetre apres : {AP.start} a {AP.stop - 1}")

print("\n=== 0. CONTEXTE DE DECLARATION DE L'INSTALLATION, flux rejets")
print("Nombre de metaux du perimetre declares et masse totale, par annee.")
print("Une chute du nombre de metaux declares oriente vers un seuil de")
print("declaration ou un changement de perimetre, pas vers ce metal seul.")
tout = D[(D["id"] == npri_id) & (D["flux"] == "rejets")]
ctx = tout.groupby("annee").agg(
    metaux_declares=("metal", "nunique"), total_kg=("kg", "sum")
)
ctx["total_kg"] = ctx["total_kg"].round(1)
ctx["fenetre"] = [_fenetre(a) for a in ctx.index]
print(ctx.to_string())

print("\n=== 1. VENTILATION PAR FLUX, kg")
print("Les trois flux ne s'additionnent jamais. Un report d'un flux vers un")
print("autre se lit ici comme une variation de sens oppose.")
f = d.pivot_table(index="annee", columns="flux", values="kg", aggfunc="sum").round(1)
f["fenetre"] = [_fenetre(a) for a in f.index]
print(f.to_string())

print("\n=== 2. GROUPES DE DECLARATION, flux rejets, kg")
print(f"Bascule a surveiller vers le groupe agrege : {inrp.GROUPE_AGREGE!r}")
r = d[d["flux"] == "rejets"]
g = r.pivot_table(index="annee", columns="groupe", values="kg", aggfunc="sum").round(1)
print(g.to_string())
if r["agrege_sous_1t"].any():
    print("\nAnnees declarees dans le groupe agrege sous une tonne :",
          sorted(r.loc[r["agrege_sous_1t"], "annee"].unique()))
else:
    print("\nAucune annee declaree dans le groupe agrege sous une tonne.")

print("\n=== 3. CATEGORIES DE REJET, flux rejets, kg")
c = r.pivot_table(index="annee", columns="categorie", values="kg", aggfunc="sum").round(1)
print(c.to_string())

print("\n=== 4. METHODES D'ESTIMATION, flux rejets, kg par annee et par code")
mm = det.masse_par_methode(D)
m = mm[(mm["id"] == npri_id) & (mm["metal"] == metal)]
pm = m.pivot_table(index="annee", columns="methode", values="kg", aggfunc="sum").round(1)
pm["fenetre"] = [_fenetre(a) for a in pm.index]
print(pm.to_string())
dom_av, liste_av = det._methodes_fenetre(mm, npri_id, metal, AV)
dom_ap, liste_ap = det._methodes_fenetre(mm, npri_id, metal, AP)
print("\n-- methode croisee avec la categorie de rejet")
print("La methode dominante par annee agrege les milieux. Un metal declare a")
print("l'air par facteur d'emission et a l'eau par echantillonnage donne une")
print("fenetre mixte sans qu'aucune methode n'ait change. Le croisement")
print("ci-dessous distingue une coexistence stable d'une vraie transition.")
pmc = r.pivot_table(
    index="annee", columns=["categorie", "methode"], values="kg", aggfunc="sum"
).round(1)
print(pmc.to_string())

print(f"\ndominante fenetre avant : {dom_av}")
print(f"codes presents avant    : {liste_av}")
print(f"dominante fenetre apres : {dom_ap}")
print(f"codes presents apres    : {liste_ap}")

print(f"\n=== 5. COMMENTAIRES DE L'EXPLOITANT, code {code}, {annee - 2} a {annee + 2}")
C2 = inrp.charger_commentaires({npri_id})
C = C2[C2["code"] == code]
C = C[C["annee"].between(annee - 2, annee + 2)].sort_values(["annee", "type"])
if C.empty:
    print("aucun commentaire pour ce code sur la fenetre")
for t in C.itertuples():
    print(f"{t.annee} | {t.type} | {t.commentaire}")

print(f"\n=== 5 bis. AUTRES COMMENTAIRES DE L'INSTALLATION, {annee - 2} a {annee + 2}")
print("Les commentaires sont rattaches a un code de substance. Un enonce qui")
print("porte sur toute l'installation, une reevaluation de facteurs d'emission")
print("ou une nouvelle campagne d'echantillonnage par exemple, n'est rattache")
print("qu'a certains codes, souvent les matieres particulaires NA - M08, M09 et")
print("M10, qui portent les poussieres dans lesquelles les metaux sont emis.")
print("Filtrer sur le seul code du metal teste rend ces enonces invisibles.")
T = inrp.charger_commentaires({npri_id})
T = T[T["annee"].between(annee - 2, annee + 2) & (T["code"] != code)]
T = T.drop_duplicates(["annee", "type", "commentaire"]).sort_values(["annee", "type"])
if T.empty:
    print("\naucun autre commentaire sur la fenetre")
for t in T.itertuples():
    codes = sorted(
        set(
            C2.loc[
                (C2["annee"] == t.annee)
                & (C2["type"] == t.type)
                & (C2["commentaire"] == t.commentaire),
                "code",
            ].astype(str)
        )
    )
    print(f"{t.annee} | {t.type} | codes {', '.join(codes)}")
    print(f"        {t.commentaire}")

print("\n=== 6. INSTALLATIONS LIEES DU MEME EXPLOITANT, meme metal, kg")
print("Comparaison restreinte au perimetre de la selection figee.")
import json

sel = json.loads(inrp.SELECTION.read_text(encoding="utf-8"))
ids_perimetre = [x["npri_id"] for x in sel["retenues"]]
liees = D[
    (D["societe"] == societe)
    & (D["metal"] == metal)
    & (D["id"].isin(ids_perimetre))
]
if liees["id"].nunique() <= 1:
    print(f"aucune autre installation de {societe!r} dans le perimetre.")
else:
    for flux in ("rejets", "eliminations", "transferts"):
        sous = liees[liees["flux"] == flux]
        if sous.empty:
            continue
        print(f"\n-- flux {flux}")
        t = sous.pivot_table(index="annee", columns="id", values="kg", aggfunc="sum").round(1)
        print(t.to_string())
