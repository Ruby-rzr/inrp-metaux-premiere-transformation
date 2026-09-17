import json
import pandas as pd
import inrp
import detection as det

det.ecrire_regle()

sel = json.loads(open("data/selection_figee.json", encoding="utf-8").read())
ids = [r["npri_id"] for r in sel["retenues"]]

proches = inrp.installations_dans_rayon()
D = inrp.charger_metaux(set(proches[inrp.COL_GEO["id"]]))
noms = D.drop_duplicates("id").set_index("id")["nom"]

S = det.series(D, ids)
c = det.annoter(det.candidates(S), det.masse_par_methode(D), noms)
a = det.arrets_declaration(S)

c.to_csv("data/derive/candidates.csv", index=False)
a.to_csv("data/derive/arrets.csv", index=False)
print(c.to_string(index=False))
print(a.to_string(index=False))