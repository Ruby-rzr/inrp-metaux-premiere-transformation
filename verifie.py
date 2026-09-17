import sys
import json
import pandas as pd
import inrp
import detection as det

pd.set_option("display.width", 200)

npri_id = int(sys.argv[1])
metal = sys.argv[2]
annee = int(sys.argv[3])

proches = inrp.installations_dans_rayon()
D = inrp.charger_metaux(set(proches[inrp.COL_GEO["id"]]))

print("=== SERIE, trois flux, kg")
d = D[(D["id"] == npri_id) & (D["metal"] == metal)]
print(d.pivot_table(index="annee", columns="flux", values="kg", aggfunc="sum").round(1))

print("\n=== GROUPES DE DECLARATION par annee")
print(d[d["flux"] == "rejets"].groupby(["annee", "groupe"])["kg"].sum().round(1))

print("\n=== METHODES par annee")
print(d[d["flux"] == "rejets"].groupby(["annee", "methode"])["kg"].sum().round(1))

print("\n=== COMMENTAIRES DE L'EXPLOITANT")
C = inrp.charger_commentaires({npri_id})
C = C[C["annee"].between(annee - 2, annee + 2)]
C = C[C["substance"].astype(str).str.contains(metal[:5], case=False, na=False)]
for r in C.itertuples():
    print(f"{r.annee} | {r.type} | {r.commentaire}")