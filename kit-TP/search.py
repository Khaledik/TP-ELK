"""Mini-défi : moteur de recherche d'offres en ligne de commande.

Exemples :
python search.py "développeur python"
python search.py "données spark" --ville Lyon --contrat CDI --salaire-min 45000
python search.py "kubernetes" --autour "43.6108,3.8767" --rayon 50km --teletravail partiel
"""

from __future__ import annotations

import argparse

from es_client import INDEX, get_client


def construire_requete(args: argparse.Namespace) -> dict:
    """Construit la requête Elasticsearch à partir des arguments."""

    # must contient la recherche texte principale
    must = [
        {
            "multi_match": {
                "query": args.texte,
                # Le titre compte plus que les compétences
                # et les compétences comptent plus que la description
                "fields": [
                    "titre^3",
                    "competences.texte^2",
                    "description"
                ],
                # Permet de tolérer quelques fautes de frappe
                "fuzziness": "AUTO"
            }
        }
    ]

    # filter contient les filtres exacts
    # Ils ne changent pas le score des résultats
    filtres = []

    # Filtre sur la ville si elle est donnée
    if args.ville:
        filtres.append(
            {
                "term": {
                    "ville": args.ville
                }
            }
        )

    # Filtre sur le contrat si il est donné
    if args.contrat:
        filtres.append(
            {
                "term": {
                    "contrat": args.contrat
                }
            }
        )

    # Filtre sur le télétravail si il est donné
    if args.teletravail:
        filtres.append(
            {
                "term": {
                    "teletravail": args.teletravail
                }
            }
        )

    # Si un salaire minimum est demandé,
    # on garde les offres dont salaire_max est supérieur ou égal
    if args.salaire_min is not None:
        filtres.append(
            {
                "range": {
                    "salaire_max": {
                        "gte": args.salaire_min
                    }
                }
            }
        )

    # Recherche autour d'un point GPS si --autour est utilisé
    if args.autour:
        try:
            lat, lon = args.autour.split(",")
            lat = float(lat)
            lon = float(lon)
        except ValueError:
            raise ValueError(
                '--autour doit être au format "latitude,longitude"'
            )

        filtres.append(
            {
                "geo_distance": {
                    "distance": args.rayon,
                    "localisation": {
                        "lat": lat,
                        "lon": lon
                    }
                }
            }
        )

    # On retourne la requête bool complète
    return {
        "bool": {
            "must": must,
            "filter": filtres
        }
    }


def afficher_facette(nom: str, buckets: list[dict]) -> None:
    """Affiche une facette de manière simple."""

    print(f"\n{nom} :")

    for bucket in buckets:
        print(f"  {bucket['key']} : {bucket['doc_count']}")


def main() -> None:
    # Arguments utilisables dans le terminal
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    p.add_argument("texte")
    p.add_argument("--ville")
    p.add_argument(
        "--contrat",
        choices=["CDI", "CDD", "Alternance", "Freelance", "Stage"]
    )
    p.add_argument(
        "--teletravail",
        choices=["aucun", "partiel", "total"]
    )
    p.add_argument("--salaire-min", type=int)
    p.add_argument("--autour", help="lat,lon")
    p.add_argument("--rayon", default="30km")
    p.add_argument("--page", type=int, default=1)
    p.add_argument("--taille", type=int, default=10)

    args = p.parse_args()

    # Petite sécurité pour éviter une page ou une taille invalide
    if args.page < 1:
        p.error("--page doit être supérieur ou égal à 1")

    if args.taille < 1:
        p.error("--taille doit être supérieur ou égal à 1")

    # Connexion à Elasticsearch
    es = get_client()

    # Construction de la requête avec les arguments du terminal
    requete = construire_requete(args)

    # Calcul du début de la page
    # Exemple : page 2 avec taille 10 = on commence au résultat 10
    debut = (args.page - 1) * args.taille

    # Envoi de la recherche à Elasticsearch
    resultat = es.search(
        index=INDEX,
        query=requete,
        from_=debut,
        size=args.taille,

        # On surligne les morceaux trouvés dans la description
        highlight={
            "fields": {
                "description": {}
            }
        },

        # Facettes affichées à la fin
        aggs={
            "villes": {
                "terms": {
                    "field": "ville",
                    "size": 12
                }
            },
            "contrats": {
                "terms": {
                    "field": "contrat",
                    "size": 5
                }
            },
            "competences": {
                "terms": {
                    "field": "competences",
                    "size": 10
                }
            }
        }
    )

    # Nombre total de résultats trouvés
    total = resultat["hits"]["total"]["value"]

    print(f"\n{total} résultat(s) trouvé(s)")
    print(f"Page {args.page}\n")

    # Affichage de chaque offre
    for hit in resultat["hits"]["hits"]:
        source = hit["_source"]

        titre = source.get("titre", "Sans titre")
        entreprise = source.get("entreprise", "Non renseignée")
        ville = source.get("ville", "Non renseignée")
        contrat = source.get("contrat", "Non renseigné")

        salaire_min = source.get("salaire_min")
        salaire_max = source.get("salaire_max")

        # Certaines offres n'ont pas de salaire
        if salaire_min is not None and salaire_max is not None:
            salaire = f"{salaire_min} - {salaire_max} €"
        else:
            salaire = "Non renseigné"

        score = hit.get("_score")

        print("=" * 70)
        print(f"Score      : {score}")
        print(f"Titre      : {titre}")
        print(f"Entreprise : {entreprise}")
        print(f"Ville      : {ville}")
        print(f"Contrat    : {contrat}")
        print(f"Salaire    : {salaire}")

        # Si Elasticsearch a trouvé un extrait à surligner,
        # on affiche le premier
        highlights = hit.get("highlight", {}).get("description", [])

        if highlights:
            print(f"Extrait    : {highlights[0]}")

    # Récupération et affichage des facettes
    aggregations = resultat["aggregations"]

    afficher_facette(
        "Villes",
        aggregations["villes"]["buckets"]
    )

    afficher_facette(
        "Contrats",
        aggregations["contrats"]["buckets"]
    )

    afficher_facette(
        "Compétences",
        aggregations["competences"]["buckets"]
    )


if __name__ == "__main__":
    main()
