# Triage des ruptures candidates

Une entrée par candidate issue de `data/derive/candidates.csv`, remplie selon
la même grille et dans le même ordre de vérification, y compris lorsque
aucune explication n'est trouvée.

Ordre de vérification appliqué à chaque candidate :

1. Ventilation par flux, pour distinguer un déplacement d'un changement de niveau
2. Groupe de déclaration, pour détecter une bascule vers le total agrégé sous une tonne
3. Catégorie de rejet, cheminée ou fugitive
4. Code de méthode d'estimation, sur les fenêtres de trois ans de part et d'autre
5. Commentaires de l'exploitant, plus ou moins deux ans
6. Installations liées du même exploitant, pour tester une cause commune

Statuts possibles : expliquée, partiellement expliquée, non expliquée.

---

## 2986 ArcelorMittal Contrecoeur Ouest, manganèse, 2014, hausse x3,75

Rejets à l'air : environ 2 100 kg par an de 2010 à 2013, plateau de 7 500 à
9 200 kg de 2014 à 2018, retour à environ 2 600 kg de 2019 à 2024.

**1. Ventilation par flux.** Les rejets dans l'eau restent entre 111 et 232 kg
sur toute la période, sans discontinuité. Les éliminations suivent un profil
distinct. Il ne s'agit donc pas d'un déplacement entre flux.

**2. Groupe de déclaration.** Stable, « Rejets à l'air » sur toute la période.
Aucune bascule vers le groupe agrégé sous une tonne.

**3. Catégorie.** Le créneau est entièrement en « Rejets de cheminée ou
ponctuels ». Aucune émission fugitive déclarée pour ce métal sur la période.

**4. Méthode d'estimation.** `E1 - Site Specific Emission Factors` de 2010 à
2017, donc inchangée de part et d'autre de 2014. Passage à
`M3 - Source Testing` en 2018, soit quatre ans après la rupture. Retour à E1
en 2024.

**5. Commentaires de l'exploitant.** Le seul commentaire portant sur les
rejets en 2014 mentionne des fluctuations normales liées à la précision de
l'échantillonnage. Le même libellé apparaît en 2013. Un plateau maintenu cinq
années consécutives n'est pas couvert par cette explication. Les autres
commentaires de 2013 et 2014 portent sur l'élimination, ouverture d'une
cellule de dépôt définitif de poussières d'aciérage.

**6. Installations liées.** Les éliminations de manganèse de Contrecoeur Ouest
passent de 284 881 à 479 163 kg en 2014, pendant que celles de Contrecoeur Est
passent de 496 650 à 280 366 kg. Déplacement quasi compensatoire, cohérent avec
le commentaire de Contrecoeur Est indiquant l'arrêt de son site d'élimination
sur place en 2014. Ce déplacement concerne l'élimination et non les rejets, et
la ventilation par catégorie exclut la piste d'émissions fugitives liées à la
manutention de poussières supplémentaires.

Les rejets de manganèse de Contrecoeur Est ne présentent pas de créneau
symétrique en 2014.

**Observation complémentaire.** La hausse de 2014 touche simultanément trois
métaux de la même installation, par des facteurs différents : cuivre x2,15,
chrome x2,34, manganèse x3,75. La méthode E1 calcule une émission comme le
produit d'un facteur d'émission par un niveau d'activité. Une variation du
niveau d'activité affecterait les trois métaux dans la même proportion. Des
facteurs divergents sont difficilement compatibles avec cette hypothèse.

Aux mêmes années, Contrecoeur Est indique dans ses commentaires sur les rejets
une mise à jour des facteurs d'émission, en 2013 et en 2014. Contrecoeur Ouest
ne mentionne aucune mise à jour de ce type.

**Statut : non expliquée par les sources consultées.**

**Ce que la preuve ne soutient pas.** Les données n'établissent pas que les
facteurs d'émission de Contrecoeur Ouest ont été révisés en 2014. Elles
n'établissent pas non plus que les rejets réels ont augmenté d'un facteur
quatre, ni que les déclarations antérieures à 2014 étaient sous-évaluées.
L'INRP ne contient aucune donnée de production permettant de tester
directement l'hypothèse d'une variation du niveau d'activité. La divergence
des facteurs entre les trois métaux rend cette hypothèse peu probable, sans
l'exclure.

**Question à adresser à l'exploitant.** Quelle est l'origine du changement de
niveau déclaré de 2014 sur les rejets atmosphériques de manganèse, de chrome
et de cuivre, et les facteurs d'émission propres au site ont-ils été révisés
entre les déclarations de 2013 et de 2014.

---

## Modèle pour les entrées suivantes

## <npri_id> <installation>, <métal>, <année>, <sens> x<ratio>

**1. Ventilation par flux.**

**2. Groupe de déclaration.**

**3. Catégorie.**

**4. Méthode d'estimation.**

**5. Commentaires de l'exploitant.**

**6. Installations liées.**

**Statut :**

**Ce que la preuve ne soutient pas.**
