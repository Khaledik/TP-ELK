# REPONSES - TP2 Logstash et analyse de logs

> État du document : exercices 0 à 4.5 terminés.  
> La partie 5 (dashboard et restitution) reste à faire.

## Mise en place

### Pourquoi ne pas utiliser le compte `elastic` pour Logstash ?

Le compte `elastic` possède beaucoup plus de droits que nécessaire.
Le pipeline utilise donc un compte dédié `logstash_internal` avec le rôle
`logstash_writer` et uniquement les droits nécessaires pour écrire dans
`offres` et `logs-web-*`.

Cela applique le principe du moindre privilège.

### Que se passerait-il si le pipeline `web` écrivait dans `logs-generic-default` ?

Le rôle autorise les index `offres` et `logs-web-*`.
`logs-generic-default` ne correspond pas à ce périmètre.

Le compte Logstash n'aurait donc pas les droits nécessaires pour y écrire.

### Pourquoi le mot de passe est-il dans une variable d'environnement ?

Le mot de passe est stocké dans `.env` et transmis au conteneur par variable
d'environnement afin de ne pas écrire le secret directement dans les fichiers
`.conf` versionnés dans Git.

---

## Exercice 0 - Premier pipeline

Quand on tape une phrase dans l'entrée `stdin`, Logstash ajoute notamment :

- `message` : texte saisi ;
- `@timestamp` : heure de création/lecture de l'événement par Logstash ;
- `@version` : version interne de l'événement ;
- `event.original` : contenu original ;
- `host.hostname` : nom du conteneur.

Avec :

`filter { mutate { uppercase => ["message"] } }`

le champ `message` est transformé en majuscules alors que `event.original`
conserve le texte d'origine.

L'option `--path.data /tmp/essai` donne à ce Logstash temporaire son propre
répertoire de données et évite un conflit avec un autre processus Logstash.

---

# Partie 1 - Recharger les offres avec Logstash

## Exercice 1.1 - Configuration

Le pipeline `offres` :

- lit `data/offres*.ndjson` en mode `read` ;
- utilise le codec `json` ;
- utilise `sincedb_path => "/dev/null"` pour relire le fichier à chaque démarrage ;
- ne supprime pas le fichier après lecture ;
- envoie les documents dans l'index `offres` ;
- utilise `document_id => "%{id}"` pour garder un `_id` métier stable ;
- n'installe pas de template car le mapping existe déjà.

La validation de configuration retourne :

`Config Validation Result: OK`

## Exercice 1.2 - Premier lancement sans correction

Avant la correction, `OFF-00002` avait :

`_version : 4`

Les documents sont rejetés par Elasticsearch avec :

- HTTP `400`
- type : `strict_dynamic_mapping_exception`

La raison observée est l'introduction du champ `event`, qui n'existe pas
dans le mapping strict de l'index `offres`.

L'événement Logstash contient aussi des champs techniques comme :

- `@timestamp`
- `@version`
- `event`
- `host`
- `log`

Ils ne sont pas prévus dans le mapping métier de `offres`.

## Exercice 1.3 - Correction

Le filtre `mutate` supprime les champs techniques ajoutés par Logstash :

`["@timestamp", "@version", "event", "log", "host"]`

Après correction :

- le nombre de documents reste à `5000` ;
- `OFF-00002` passe de `_version: 4` à `_version: 5`.

Le nombre ne double pas grâce à :

`document_id => "%{id}"`

Chaque offre conserve le même `_id`, donc elle est réindexée au lieu d'être
créée une deuxième fois.

On préfère supprimer les champs techniques plutôt que d'assouplir
`"dynamic": "strict"` afin de garder un mapping contrôlé.

L'index `offres` doit exister avant le pipeline car `manage_template => false`
indique que Logstash ne doit pas gérer le mapping à notre place.

## Exercice 1.4 - Relancer

Après un nouveau redémarrage :

- `_count` reste à `5000` ;
- `OFF-00002` passe de `_version: 5` à `_version: 6`.

Avec `sincedb_path => "/dev/null"`, Logstash ne mémorise pas la position de
lecture et relit le fichier à chaque redémarrage.

Avec la sincedb par défaut, il mémoriserait jusqu'où le fichier a été lu.

Sans `document_id`, Elasticsearch générerait de nouveaux identifiants et
les relances créeraient des doublons.

---

# Partie 2 - Superviser et fiabiliser

## Exercice 2.1 - Supervision

Deux pipelines sont chargés :

- `offres`
- `web`

Ils utilisent chacun `16` workers.

Pour le pipeline `offres`, après le dernier démarrage :

- `in` : 5000
- `filtered` : 5000
- `out` : 5000

Ces compteurs représentent les événements traités depuis le démarrage du
pipeline.

Le plugin qui consomme le plus de temps est la sortie `elasticsearch` :

- Elasticsearch : environ `8255 ms`
- mutate : environ `524 ms`

La file utilisée est de type `memory`.

## Exercice 2.2 - Dead Letter Queue

La DLQ a été activée avec :

`DEAD_LETTER_QUEUE_ENABLE=true`

Un document de test `OFF-99999` contenant :

`"prime": 3000`

a été volontairement envoyé.

Résultat :

- `OFF-99999` n'est pas présent dans l'index ;
- `_count` reste à `5000` ;
- le document est présent dans la DLQ du pipeline `offres`.

La raison enregistrée est :

- HTTP `400`
- `strict_dynamic_mapping_exception`
- champ refusé : `prime`

La DLQ conserve le document rejeté ainsi que la raison du rejet.

Par rapport à `raise_on_error=False` dans `ingest.py`, elle permet de conserver
durablement les événements en erreur afin de les analyser plus tard.

Pour corriger et réinjecter un document :

1. lire la DLQ et identifier la cause ;
2. corriger le document ou le mapping si le nouveau champ est réellement voulu ;
3. réinjecter le document corrigé dans Elasticsearch.

## Exercice 2.3 - Pourquoi deux pipelines ?

Sans `pipelines.yml`, les fichiers `.conf` seraient chargés dans un unique
pipeline `main`.

Les entrées et sorties seraient alors mélangées :

- une offre pourrait partir vers la sortie `offres` et vers la sortie web ;
- un log web pourrait lui aussi être envoyé aux deux destinations.

L'isolation des pipelines permet notamment :

- d'éviter le mélange des flux ;
- de superviser séparément les pipelines ;
- d'avoir des compteurs et erreurs distincts ;
- de faire évoluer un flux indépendamment de l'autre.

## Exercice 2.4 - Ne rien perdre

Avec une queue en mémoire, des événements déjà lus mais pas encore envoyés
peuvent être perdus si Logstash est arrêté brutalement.

Le réglage :

`queue.type: persisted`

permet d'utiliser une file persistée sur disque.

On obtient alors une garantie de traitement "au moins une fois".

Un événement pouvant être rejoué, un `document_id` métier stable devient
important afin d'éviter les doublons.

---

# Partie 3 - Transformer les logs d'accès

## Exercice 3.1 - Génération

Le script a généré :

`20700 lignes`

dans `data/access.log`.

## Exercice 3.2 - Grok

Avec `%{COMBINEDAPACHELOG}`, Grok extrait notamment :

- l'adresse IP ;
- la méthode HTTP ;
- l'URL ;
- le code HTTP ;
- la taille de réponse ;
- le referrer ;
- le user-agent ;
- le champ texte `timestamp`.

Dans le Grok Debugger, le code HTTP apparaît initialement sous forme de texte.

`timestamp` doit encore être traité par le filtre `date`.
Sinon `@timestamp` représenterait l'heure de lecture par Logstash au lieu de
l'heure réelle de la requête HTTP.

Le motif personnalisé :

`^/offres/%{OFFRE_ID:offre_id}`

avec :

`OFFRE_ID OFF-[0-9]{5}`

extrait correctement :

`OFF-01468`

depuis `/offres/OFF-01468/postuler`.

## Exercice 3.3 - Pipeline web

Le pipeline `web` utilise :

- `grok` pour structurer la ligne Apache ;
- `date` pour construire le bon `@timestamp` ;
- `useragent` pour analyser le navigateur et l'OS ;
- un second `grok` pour extraire `labels.offre_id` ;
- une sortie data stream `logs-web-default`.

## Exercice 3.4 - Vérification du data stream

Résultats :

- documents : `20700`
- `_grokparsefailure` : `0`

Backing index :

`.ds-logs-web-default-2026.10.01-000001`

Il s'agit de la première génération du data stream `logs-web-default`.

Le premier événement possède :

`@timestamp = 2026-09-22T22:00:39.000Z`

ce qui correspond au 23/09/2026 à 00:00:39 en UTC+02:00.

Le champ :

`http.response.status_code`

est de type :

`long`

Cela permet de faire correctement des comparaisons numériques comme
`>= 500`.

Le mode d'index utilisé est :

`logsdb`

## Exercice 3.5 - Rejouer sans doublon ?

Le pipeline `web` utilise :

`sincedb_path => "/dev/null"`

Le fichier est donc relu après un redémarrage.

Contrairement au pipeline `offres`, aucun `document_id` métier stable n'est
défini pour les logs.

Une vérification ciblée sur le premier événement montre qu'il apparaît deux
fois après rejeu : il y a donc bien création de doublons.

Deux solutions possibles :

1. utiliser une sincedb normale pour mémoriser la position de lecture ;
2. générer un identifiant stable à partir du contenu avec `fingerprint`.

Après le test, le data stream a été supprimé puis recréé afin de repartir avec
`20700` événements propres.

---

# Partie 4 - Enquête dans Kibana

## Exercice 4.1 - Vue d'ensemble

### Codes HTTP

Répartition exacte :

- `200` : 17805
- `201` : 1492
- `304` : 488
- `404` : 508
- `500` : 5
- `503` : 402

La grande majorité des requêtes réussit.

Les `402` réponses 503 montrent cependant un incident serveur à investiguer.

### Méthodes HTTP

- `GET` : 19208
- `POST` : 1492

Le trafic est donc très majoritairement composé de requêtes GET.

### Volume journalier

- 23 septembre : 2832
- 24 septembre : 2884
- 25 septembre : 2843
- 26 septembre : 3122
- 27 septembre : 2903
- 28 septembre : 3274
- 29 septembre : 2842

Moyenne :

`2957,143 requêtes par jour`

## Exercice 4.2 - Incident

L'incident a lieu le :

`28 septembre 2026`

entre environ :

`14h00 et 14h45`

On observe `402` réponses 5xx pendant l'heure de 14h.

Les erreurs concernent l'API :

`/api/offres?ville=...&page=...`

Principales URL touchées :

- Bordeaux page 1 : 71 erreurs
- Lyon page 1 : 67
- Lille page 1 : 61
- Paris page 1 : 54
- Nantes page 1 : 53
- Montpellier page 1 : 48
- Toulouse page 1 : 46

Les pages normales du site, les fiches d'offres, les recherches, les
candidatures et les fichiers statiques ne sont pas touchés.

Pendant l'incident, le volume de requêtes API augmente très fortement.

Juste avant, on observe seulement quelques requêtes par tranche de 5 minutes.
À partir de 14h, on passe à plusieurs dizaines de requêtes par tranche.

Une explication probable est que les clients reçoivent des réponses 503 et
réessaient leurs requêtes, ce qui augmente encore la charge.

## Exercice 4.3 - Activité suspecte

Adresse IP suspecte :

`203.0.113.66`

Elle génère :

`300 réponses 404`

entre :

- début : 26/09/2026 à 03:12:00
- fin : 26/09/2026 à 03:16:59

Durée : environ 5 minutes.

URLs testées :

- `/admin` : 59
- `/.git/config` : 55
- `/.env` : 53
- `/phpmyadmin/` : 46
- `/server-status` : 44
- `/wp-login.php` : 43

Ces chemins correspondent à des interfaces d'administration ou à des fichiers
sensibles. Le comportement ressemble donc à un scan automatisé de
vulnérabilités.

User-agent du scan :

`Mozilla/5.0 zgrab/0.x`

Il se distingue d'un navigateur humain car `zgrab` est un outil automatisé.

Les autres 404 concernent surtout des URLs d'offres inexistantes comme :

`/offres/OFF-09347`

Elles sont dispersées, avec seulement quelques occurrences chacune, et sont
donc beaucoup moins inquiétantes que la rafale du robot.

## Exercice 4.4 - Offres les plus consultées

| Offre | Consultations | Titre | Ville | Contrat |
| --- | ---: | --- | --- | --- |
| OFF-04662 | 8 | Développeur Front-end Senior | Bordeaux | Freelance |
| OFF-01153 | 7 | Développeur Java Confirmé | Toulouse | Freelance |
| OFF-03141 | 7 | Développeur Python Confirmé | Bordeaux | CDI |
| OFF-02899 | 6 | Data Engineer (Alternance) | Lyon | Alternance |
| OFF-01275 | 6 | Administrateur Bases de Données Lead | Paris | CDI |
| OFF-01660 | 6 | Architecte Cloud Senior | Lyon | CDI |
| OFF-03923 | 6 | Architecte Cloud Confirmé | Lyon | CDI |
| OFF-00901 | 6 | Développeur Java Junior | Paris | CDI |
| OFF-03145 | 6 | Data Engineer Lead | Montpellier | CDI |
| OFF-03524 | 6 | Développeur Python (Alternance) | Toulouse | Alternance |

Les informations métier ont été récupérées dans l'index `offres` avec une
seule requête `ids`.

## Exercice 4.5 - Le public

Répartition par système :

- Mac OS X : 4150
- iOS : 4099
- Windows : 4058
- Android : 4056
- Linux : 4037
- Other : 300

Les appareils mobiles sont iOS et Android :

`4099 + 4056 = 8155`

Soit environ :

`8155 / 20700 = 39,4 %`

du trafic.

Les trois navigateurs les plus utilisés sont :

1. Safari : 4150
2. Mobile Safari : 4099
3. Chrome : 4058

---

# Partie 5 - Dashboard

Un tableau de bord Kibana nommé `Site de recrutement - trafic`
a été créé.

Il contient :

- le nombre total de requêtes : 20 700 ;
- le taux d'erreur serveur : 1,97 % ;
- le trafic dans le temps, réparti par code HTTP ;
- les 10 offres les plus consultées ;
- les 5 navigateurs les plus utilisés ;
- une carte des offres basée sur le champ `localisation`.

L'interactivité a également été testée.

Un clic sur une barre correspondant au code HTTP 503 applique
un filtre au tableau de bord et met à jour les autres visualisations.
