# Partie 3 : Recherche et analyseurs


# Exercice 3.1 : Analyseurs


```http
POST _analyze
{
  "analyzer": "standard",
  "text": "Les développeuses travaillaient sur l'analyse des données"
}

POST _analyze
{
  "analyzer": "french",
  "text": "Les développeuses travaillaient sur l'analyse des données"
}

POST _analyze
{
  "analyzer": "standard",
  "text": "donnée données"
}

POST _analyze
{
  "analyzer": "french",
  "text": "donnée données"
}


```

# Exercice 3.2 : match contre term


```http
GET offres/_search
{
  "query": {
    "match": {
      "description": "projets bancaires"
    }
  }
}

GET offres/_search
{
  "query": {
    "term": {
      "ville": "paris"
    }
  }
}

GET offres/_search
{
  "query": {
    "term": {
      "titre": "Data Engineer Senior"
    }
  }
}

```

# Corrections des term


```http
GET offres/_search
{
  "query": {
    "term": {
      "ville": "Paris"
    }
  }
}

GET offres/_search
{
  "query": {
    "term": {
      "titre.brut": "Data Engineer Senior"
    }
  }
}

```

# match avec AND


```http
GET offres/_search
{
  "query": {
    "match": {
      "description": {
        "query": "projets bancaires",
        "operator": "and"
      }
    }
  }
}


```

# Exercice 3.3 : multi_match, fuzziness et boost


```http
GET offres/_search
{
  "query": {
    "multi_match": {
      "query": "kubernetis terraform",
      "fields": [
        "titre",
        "competences.texte",
        "description"
      ]
    }
  }
}

GET offres/_search
{
  "query": {
    "multi_match": {
      "query": "kubernetis terraform",
      "fields": [
        "titre",
        "competences.texte",
        "description"
      ],
      "fuzziness": "AUTO"
    }
  }
}

GET offres/_search
{
  "query": {
    "multi_match": {
      "query": "kubernetis terraform",
      "fields": [
        "titre^3",
        "competences.texte",
        "description"
      ],
      "fuzziness": "AUTO"
    }
  }
}


```

# Exercice 3.4 : requête bool


```http
GET offres/_search
{
  "query": {
    "bool": {
      "must": [
        {
          "multi_match": {
            "query": "données",
            "fields": [
              "titre",
              "description"
            ]
          }
        }
      ],
      "filter": [
        {
          "term": {
            "contrat": "CDI"
          }
        },
        {
          "terms": {
            "ville": [
              "Montpellier",
              "Toulouse"
            ]
          }
        },
        {
          "range": {
            "salaire_max": {
              "gte": 50000
            }
          }
        }
      ],
      "must_not": [
        {
          "term": {
            "teletravail": "aucun"
          }
        }
      ],
      "should": [
        {
          "term": {
            "competences": "Elasticsearch"
          }
        }
      ]
    }
  }
}

```

# Même requête sans should pour comparer les scores


```http
GET offres/_search
{
  "query": {
    "bool": {
      "must": [
        {
          "multi_match": {
            "query": "données",
            "fields": [
              "titre",
              "description"
            ]
          }
        }
      ],
      "filter": [
        {
          "term": {
            "contrat": "CDI"
          }
        },
        {
          "terms": {
            "ville": [
              "Montpellier",
              "Toulouse"
            ]
          }
        },
        {
          "range": {
            "salaire_max": {
              "gte": 50000
            }
          }
        }
      ],
      "must_not": [
        {
          "term": {
            "teletravail": "aucun"
          }
        }
      ]
    }
  }
}


```

# Exercice 3.5 : recherche géographique


```http
GET offres/_search
{
  "query": {
    "bool": {
      "filter": {
        "geo_distance": {
          "distance": "20km",
          "localisation": {
            "lat": 43.6108,
            "lon": 3.8767
          }
        }
      }
    }
  },
  "sort": [
    {
      "_geo_distance": {
        "localisation": {
          "lat": 43.6108,
          "lon": 3.8767
        },
        "order": "asc",
        "unit": "km"
      }
    }
  ]
}


```

# Exercice 3.6 : pagination et highlight


```http
GET offres/_search
{
  "from": 5,
  "size": 5,
  "_source": [
    "titre",
    "entreprise",
    "ville"
  ],
  "query": {
    "bool": {
      "must": [
        {
          "multi_match": {
            "query": "données",
            "fields": [
              "titre",
              "description"
            ]
          }
        }
      ],
      "filter": [
        {
          "term": {
            "contrat": "CDI"
          }
        },
        {
          "terms": {
            "ville": [
              "Montpellier",
              "Toulouse"
            ]
          }
        },
        {
          "range": {
            "salaire_max": {
              "gte": 50000
            }
          }
        }
      ],
      "must_not": [
        {
          "term": {
            "teletravail": "aucun"
          }
        }
      ],
      "should": [
        {
          "term": {
            "competences": "Elasticsearch"
          }
        }
      ]
    }
  },
  "highlight": {
    "fields": {
      "description": {}
    }
  }
}
```
