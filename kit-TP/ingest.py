"""Script pour créer l'index `offres` et ajouter les offres dans Elasticsearch.

Utilisation :
python ingest.py
python ingest.py --reset
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterator
from pathlib import Path

from elasticsearch import helpers

from es_client import INDEX, get_client


# Configuration de base de l'index
# On utilise 1 shard et 0 replica car on travaille sur un seul noeud
SETTINGS = {
    "number_of_shards": 1,
    "number_of_replicas": 0
}


# Ici on définit les types de chaque champ de nos offres
# dynamic strict permet de refuser un champ qui n'est pas prévu ici
MAPPINGS = {
    "dynamic": "strict",
    "properties": {
        "id": {"type": "keyword"},
        "entreprise": {"type": "keyword"},
        "ville": {"type": "keyword"},
        "contrat": {"type": "keyword"},
        "teletravail": {"type": "keyword"},

        # Le titre sert à la recherche texte
        # Le sous-champ brut sert pour les tris ou les filtres exacts
        "titre": {
            "type": "text",
            "analyzer": "french",
            "fields": {
                "brut": {"type": "keyword"}
            }
        },

        # La description est un texte sur lequel on veut faire des recherches
        "description": {
            "type": "text",
            "analyzer": "french"
        },

        # Les compétences servent à la fois pour les filtres exacts
        # et pour la recherche texte avec competences.texte
        "competences": {
            "type": "keyword",
            "fields": {
                "texte": {
                    "type": "text",
                    "analyzer": "french"
                }
            }
        },

        # geo_point permet de stocker latitude et longitude
        "localisation": {"type": "geo_point"},

        # Les champs numériques
        "experience_annees": {"type": "integer"},
        "salaire_min": {"type": "integer"},
        "salaire_max": {"type": "integer"},

        # Le champ date
        "date_publication": {"type": "date"}
    }
}


def lire_actions(fichier: Path) -> Iterator[dict]:
    """Lit le fichier offre par offre et prépare les données pour Elasticsearch."""

    # On ouvre le fichier en UTF-8 pour bien garder les accents
    with fichier.open("r", encoding="utf-8") as f:

        # On lit une ligne à la fois
        for ligne in f:
            ligne = ligne.strip()

            # Si la ligne est vide on passe à la suivante
            if not ligne:
                continue

            # On transforme la ligne JSON en dictionnaire Python
            document = json.loads(ligne)

            # yield permet d'envoyer les documents un par un
            # sans charger tout le fichier en mémoire
            yield {
                "_index": INDEX,

                # On utilise l'id de l'offre comme id Elasticsearch
                # Cela évite de créer des doublons si on relance le script
                "_id": document["id"],

                # Le document complet sera enregistré dans _source
                "_source": document
            }


def main() -> None:
    # Permet de gérer les options données dans le terminal
    parser = argparse.ArgumentParser(description=__doc__)

    # Par défaut on utilise le fichier data/offres.ndjson
    parser.add_argument(
        "--fichier",
        type=Path,
        default=Path("data/offres.ndjson")
    )

    # Si on ajoute --reset, on supprimera l'ancien index
    parser.add_argument(
        "--reset",
        action="store_true",
        help="supprime l'index s'il existe"
    )

    args = parser.parse_args()

    # Connexion à Elasticsearch grâce au fichier es_client.py
    es = get_client()

    # On affiche la version du cluster pour vérifier que la connexion marche
    print("Cluster :", es.info()["version"]["number"])


    # Si on a lancé le script avec --reset
    # on supprime l'ancien index offres
    if args.reset:
        es.indices.delete(
            index=INDEX,
            ignore_unavailable=True
        )

        print(f"Index '{INDEX}' supprimé")


    # Si l'index n'existe pas encore, on le crée
    if not es.indices.exists(index=INDEX):
        es.indices.create(
            index=INDEX,
            settings=SETTINGS,
            mappings=MAPPINGS
        )

        print(f"Index '{INDEX}' créé")


    # On envoie les documents à Elasticsearch par groupes de 1000
    # raise_on_error=False permet de récupérer les erreurs sans arrêter tout le script
    succes, erreurs = helpers.bulk(
        es,
        lire_actions(args.fichier),
        chunk_size=1000,
        raise_on_error=False
    )

    print(f"{succes} documents indexés")
    print(f"{len(erreurs)} erreurs")


    # S'il y a des erreurs, on les affiche
    if erreurs:
        for erreur in erreurs:
            print(erreur)


    # On force le refresh pour rendre les nouveaux documents visibles immédiatement
    es.indices.refresh(index=INDEX)


    # On compte le nombre de documents présents dans l'index
    nombre = es.count(index=INDEX)["count"]

    print(f"{nombre} documents dans '{INDEX}'")


# Ce bloc lance main() seulement si on exécute directement ce fichier
if __name__ == "__main__":
    main()
