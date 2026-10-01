# REPONSES : TP Introduction à Elasticsearch

## Exercice 0 : accès au cluster

Les requêtes envoyées depuis Kibana ou un autre client HTTP donnent le même résultat si on appelle la même API avec les mêmes paramètres.

Sans authentification, Elasticsearch refuse l'accès avec un code HTTP 401.

Kibana ne demande pas le mot de passe à chaque requête car on est déjà connecté dans l'interface. Kibana utilise ensuite la session authentifiée pour envoyer les requêtes à Elasticsearch.


# Partie 1 : Concepts, CRUD et mapping

## Exercice 1.1 : Explorer le cluster

### Quelle version tourne ?

La version utilisée est Elasticsearch 9.5.4.

### Combien de nœuds ?

Il y a un seul nœud : `es01`.

### Pourquoi certains index commencent par un point ?

Ce sont des index système utilisés par Elasticsearch et Kibana. Ils servent par exemple à stocker des informations internes de Kibana, de sécurité ou de monitoring.


## Exercice 1.2 : CRUD

### Comment évolue `_version` ?

À la création du document, `_version` vaut 1.

Après la mise à jour du document, `_version` passe à 2.

La version augmente donc à chaque écriture sur le document.

### Quel identifiant reçoit le document créé avec `POST essai/_doc` ?

Elasticsearch génère automatiquement un identifiant.

Dans mon test, l'identifiant généré était :

`-ZuS7KABb-67R1-EqRmy`

### L'index `essai` existait-il avant le premier `PUT` ?

Non.

Elasticsearch a créé automatiquement l'index `essai` lors du premier `PUT`.


## Exercice 1.3 : Les pièges du mapping dynamique

### Quel type reçoit `salaire` ?

`salaire` est détecté comme `text` car la première valeur envoyée était `"45000"` avec des guillemets.

### Quel type reçoit `publication` ?

`publication` est détecté comme `date`.

### Quel type reçoit `actif` ?

`actif` est détecté comme `text` car `"true"` a été envoyé sous forme de texte.

### Pourquoi le document 2 est-il accepté ?

Le mapping du champ `salaire` était déjà défini en `text`.

Elasticsearch accepte quand même la valeur numérique `52000` et l'indexe selon le type déjà défini.

### Quelle conséquence pour un tri ou un filtre `salaire > 50000` ?

Le champ est mal typé pour une comparaison numérique.

Un salaire doit être un type numérique pour pouvoir faire correctement des tris, des filtres par intervalle ou des moyennes.

Cela montre le risque de laisser Elasticsearch choisir automatiquement le mapping à partir du premier document.


## Exercice 1.4 : Mapping explicite

### Quelle erreur obtient-on avec `champ_inconnu` ?

On obtient une erreur :

`strict_dynamic_mapping_exception`

Le mapping est configuré avec :

`"dynamic": "strict"`

donc Elasticsearch refuse les champs qui ne sont pas déclarés.

### Pourquoi est-ce une bonne pratique ?

Cela évite d'ajouter par erreur des champs mal nommés ou non prévus.

Cela permet aussi de garder un mapping propre et contrôlé.


# Partie 2 : Ingestion Python

## Exercice 2.2 : Idempotence et identifiants

### Le nombre de documents a-t-il doublé ?

Non.

Après avoir relancé `python ingest.py`, il y avait toujours 5000 documents.

### Pourquoi fixer `_id` avec le champ `id` est essentiel ?

Chaque offre garde toujours le même identifiant Elasticsearch.

Quand on relance l'ingestion, Elasticsearch remplace le document qui possède déjà cet `_id` au lieu d'en créer un nouveau.

### Que se passerait-il avec des identifiants générés automatiquement ?

Chaque nouvelle ingestion créerait de nouveaux documents.

On aurait donc des doublons et le nombre de documents augmenterait à chaque lancement.


## Exercice 2.3 : Erreur de mapping

J'ai ajouté un document `OFF-99999` avec un champ :

`"prime": 3000`

Le résultat était :

`strict_dynamic_mapping_exception`

### Le lot entier est-il rejeté ?

Non.

5000 documents ont été indexés correctement et seulement le document invalide a été rejeté.

### Quel est l'intérêt de `raise_on_error=False` ?

Cela permet au pipeline de continuer même si un document contient une erreur.

Les documents valides sont importés et les erreurs peuvent être récupérées et affichées séparément.


## Exercice 2.4 : Vérification

L'index `offres` contient bien 5000 documents.

Le document `OFF-00002` est bien présent.

La Data View `offres` a été créée dans Kibana avec `date_publication` comme champ temporel.


# Partie 3 : Recherche et analyseurs

## Exercice 3.1 : Analyseurs

### Que fait l'analyseur `standard` ?

Avec :

`Les développeuses travaillaient sur l'analyse des données`

il garde les tokens suivants :

- les
- développeuses
- travaillaient
- sur
- l'analyse
- des
- données

### Que fait l'analyseur `french` ?

Il produit :

- developeu
- travailaient
- analys
- done

Les mots `les`, `sur` et `des` disparaissent.

`l'analyse` devient `analys`.

### Comparaison entre `donnée` et `données`

Avec `standard` :

- donnée
- données

Les deux tokens sont différents.

Avec `french` :

- done
- done

Les deux formes deviennent le même terme.

### Conclusion

L'analyseur français est mieux adapté à la recherche en français car il supprime certains mots peu utiles et rapproche plusieurs formes d'un même mot.


## Exercice 3.2 : `match` contre `term`

### Pourquoi `term` sur `"paris"` retourne 0 résultat ?

Le champ `ville` est de type `keyword`.

`term` cherche une valeur exacte et ne transforme pas le texte.

La valeur enregistrée est `Paris` et non `paris`.

La correction est :

`"ville": "Paris"`

Cette requête a renvoyé 1492 résultats.

### Pourquoi `term` sur `titre` retourne 0 résultat ?

`titre` est un champ `text`, donc il est analysé.

Pour chercher le titre complet comme une valeur exacte, il faut utiliser le sous-champ `titre.brut` en `keyword`.

La requête sur :

`"titre.brut": "Data Engineer Senior"`

a renvoyé 103 résultats.

### Effet de `operator: "and"`

La requête `match` sur `"projets bancaires"` renvoyait 4190 résultats avec le comportement par défaut.

Avec :

`"operator": "and"`

elle renvoie 393 résultats.

Avec `and`, les deux termes doivent être présents.


## Exercice 3.3 : `multi_match`, fuzziness et boost

Sans `fuzziness`, la recherche :

`kubernetis terraform`

a renvoyé 739 résultats.

Avec :

`"fuzziness": "AUTO"`

elle a renvoyé 969 résultats.

### Quel paramètre rattrape la faute ?

`fuzziness` permet de retrouver `Kubernetes` même si on écrit `kubernetis`.

### Effet de `titre^3`

Dans mon test, le boost `titre^3` n'a pas modifié les premiers résultats ni le score maximum.

Les termes recherchés étaient surtout présents dans les compétences et les descriptions, pas dans les titres des premiers résultats.


## Exercice 3.4 : Requête `bool`

La requête retourne 25 résultats.

Avec le bloc `should` :

`max_score = 4.0144134`

Sans le bloc `should` :

`max_score = 2.0479767`

Le nombre de résultats reste à 25.

### Effet du `should`

Le `should` ne rend pas la compétence Elasticsearch obligatoire.

Il donne un bonus de score aux offres qui possèdent cette compétence et peut donc changer leur classement.

### Pourquoi utiliser `filter` pour les critères exacts ?

Première raison : les filtres ne calculent pas de score inutile.

Deuxième raison : les filtres peuvent être mis en cache, ce qui est plus efficace.


## Exercice 3.5 : Recherche géographique

La recherche à moins de 20 km de Montpellier renvoie 340 offres.

Les résultats sont triés de la plus proche à la plus éloignée.

La première offre est à environ 0,188 km du point donné.

Le `_score` vaut `null` car le classement se fait avec la distance et non avec la pertinence d'une recherche textuelle.


## Exercice 3.6 : Pagination et surlignage

Avec :

`from: 5`

et :

`size: 5`

on obtient la page 2 avec 5 résultats.

### Pourquoi `from + size` est limité à 10000 ?

Une pagination très profonde demande beaucoup de mémoire et de calcul car Elasticsearch doit récupérer et trier beaucoup de résultats avant de retourner la page demandée.

Au-delà, il faut utiliser `search_after` avec un Point In Time, appelé PIT.


# Partie 4 : Agrégations

## Exercice 4.1 : Offres et salaire moyen par ville

### Quelle ville a le salaire moyen le plus élevé ?

Paris est en première position avec un salaire minimum moyen d'environ :

`57 442 €`

### Sur combien d'offres la moyenne est-elle réellement calculée ?

3389 offres possèdent le champ `salaire_min`.

Les autres offres n'ont pas de salaire, notamment certains contrats comme l'alternance, le stage ou le freelance.

### Que se passe-t-il si on agrège sur `titre` ?

On obtient une erreur :

`Fielddata is disabled on [titre]`

Le champ `titre` est en `text` et n'est pas adapté directement aux agrégations.

### Comment corriger ?

Il faut utiliser :

`titre.brut`

car ce sous-champ est de type `keyword`.


## Exercice 4.2 : Publications par mois

Le `date_histogram` a regroupé les 5000 offres entre avril et septembre 2026.

Chaque mois contient ensuite une sous-agrégation avec les différents contrats :

- CDI
- CDD
- Alternance
- Freelance
- Stage

Cela permet de voir la répartition des contrats pour chaque mois.


## Exercice 4.3 : Tranches de salaire et statistiques

Répartition des 3389 offres qui ont un salaire :

- moins de 40 k : 484 offres
- de 40 k à 55 k : 1363 offres
- 55 k ou plus : 1542 offres

Pour l'expérience demandée :

- minimum : 0 an
- maximum : 15 ans
- moyenne : 5,9128 ans
- somme : 29564 années sur les 5000 offres


## Exercice 4.4 : Requête et agrégations

J'ai utilisé `match_phrase` pour sélectionner précisément les titres contenant `Data Engineer`.

Nombre d'offres Data Engineer trouvées :

462

### Les 5 compétences les plus demandées

1. Airflow : 315
2. Spark : 313
3. Kafka : 312
4. Python : 311
5. SQL : 301

### Télétravail le plus fréquent

Le télétravail partiel est le plus fréquent :

- partiel : 284
- aucun : 109
- total : 69

### L'agrégation porte-t-elle sur tout l'index ?

Non.

Les agrégations sont calculées uniquement sur les 462 documents sélectionnés par la requête.


## Exercice 4.5 : Visualisation Kibana

Une visualisation Lens a été créée avec :

- axe horizontal : `ville`
- axe vertical : nombre d'offres
- découpage des barres : `contrat`
- 12 valeurs de ville

La visualisation a été enregistrée sous le nom :

`Offres par ville et contrat`


# Mini-défi : moteur de recherche

Le script `search.py` fonctionne avec les trois tests demandés.

## Test 1

Commande :

`python search.py "développeur python"`

Résultat :

3996 résultats.

Les offres `Développeur Python` sont bien placées dans les premiers résultats.

Les facettes ville, contrat et compétences sont affichées.


## Test 2

Commande :

`python search.py "données spark" --ville Lyon --contrat CDI --salaire-min 45000`

Résultat :

180 résultats.

Les résultats respectent les filtres :

- ville : Lyon
- contrat : CDI
- salaire maximum supérieur ou égal à 45000


## Test 3

Commande :

`python search.py "kubernetes" --autour "43.6108,3.8767" --rayon 50km --teletravail partiel --page 2`

Résultat :

33 résultats.

La page 2 est bien affichée.

Les résultats sont autour de Montpellier et respectent le filtre sur le télétravail.

La facette compétences contient notamment :

`Kubernetes : 31`
