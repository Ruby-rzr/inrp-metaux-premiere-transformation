import json
import inrp

manifeste = inrp.manifeste_local()
print("fichiers archives :", list(manifeste))

proches = inrp.installations_dans_rayon()
print("installations dans le rayon :", len(proches))

D = inrp.charger_metaux(set(proches[inrp.COL_GEO["id"]]))
print("lignes metaux :", len(D))

selection = inrp.figer_selection(D, proches)
print(json.dumps(selection, indent=2, ensure_ascii=False))