# Partie 1 : Concepts, CRUD et mapping


# Exercice 1.1 : Explorer le cluster


```http
GET /

GET _cat/nodes?v

GET _cat/indices?v&expand_wildcards=all


```

# Exercice 1.2 : CRUD


```http
PUT essai/_doc/1
{
  "titre": "Data Engineer",
  "ville": "Montpellier"
}

GET essai/_doc/1

POST essai/_update/1
{
  "doc": {
    "contrat": "CDI"
  }
}

GET essai/_doc/1

POST essai/_doc
{
  "titre": "DevOps",
  "ville": "Lyon"
}

DELETE essai/_doc/1

GET essai/_doc/1


```

# Exercice 1.3 : Mapping dynamique


```http
PUT essai2/_doc/1
{
  "salaire": "45000",
  "publication": "2026-08-02",
  "actif": "true"
}

PUT essai2/_doc/2
{
  "salaire": 52000
}

GET essai2/_mapping


```

# Exercice 1.4 : Mapping explicite de l'index offres


```http
PUT offres
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0
  },
  "mappings": {
    "dynamic": "strict",
    "properties": {
      "id": {
        "type": "keyword"
      },
      "entreprise": {
        "type": "keyword"
      },
      "ville": {
        "type": "keyword"
      },
      "contrat": {
        "type": "keyword"
      },
      "teletravail": {
        "type": "keyword"
      },
      "titre": {
        "type": "text",
        "analyzer": "french",
        "fields": {
          "brut": {
            "type": "keyword"
          }
        }
      },
      "description": {
        "type": "text",
        "analyzer": "french"
      },
      "competences": {
        "type": "keyword",
        "fields": {
          "texte": {
            "type": "text",
            "analyzer": "french"
          }
        }
      },
      "localisation": {
        "type": "geo_point"
      },
      "experience_annees": {
        "type": "integer"
      },
      "salaire_min": {
        "type": "integer"
      },
      "salaire_max": {
        "type": "integer"
      },
      "date_publication": {
        "type": "date"
      }
    }
  }
}

```

# Test du mapping strict


```http
PUT offres/_doc/test
{
  "champ_inconnu": 1
}

```

# Nettoyage des index de test


```http
DELETE essai

DELETE essai2
```
