# Partie 4 : Agrégations


# Exercice 4.1 : salaire moyen par ville


```http
GET offres/_search
{
  "size": 0,
  "aggs": {
    "par_ville": {
      "terms": {
        "field": "ville",
        "size": 12,
        "order": {
          "salaire_moyen": "desc"
        }
      },
      "aggs": {
        "salaire_moyen": {
          "avg": {
            "field": "salaire_min"
          }
        }
      }
    }
  }
}

```

# Vérification du nombre d'offres avec salaire


```http
GET offres/_count
{
  "query": {
    "exists": {
      "field": "salaire_min"
    }
  }
}

```

# Test volontaire sur un champ text


```http
GET offres/_search
{
  "size": 0,
  "aggs": {
    "par_titre": {
      "terms": {
        "field": "titre"
      }
    }
  }
}

```

# Correction avec le sous-champ keyword


```http
GET offres/_search
{
  "size": 0,
  "aggs": {
    "par_titre": {
      "terms": {
        "field": "titre.brut"
      }
    }
  }
}


```

# Exercice 4.2 : publications par mois et contrat


```http
GET offres/_search
{
  "size": 0,
  "aggs": {
    "par_mois": {
      "date_histogram": {
        "field": "date_publication",
        "calendar_interval": "month"
      },
      "aggs": {
        "par_contrat": {
          "terms": {
            "field": "contrat"
          }
        }
      }
    }
  }
}


```

# Exercice 4.3 : tranches de salaire et statistiques d'expérience


```http
GET offres/_search
{
  "size": 0,
  "aggs": {
    "tranches_salaire": {
      "range": {
        "field": "salaire_min",
        "ranges": [
          {
            "key": "< 40 k",
            "to": 40000
          },
          {
            "key": "40-55 k",
            "from": 40000,
            "to": 55000
          },
          {
            "key": ">= 55 k",
            "from": 55000
          }
        ]
      }
    },
    "stats_experience": {
      "stats": {
        "field": "experience_annees"
      }
    }
  }
}


```

# Exercice 4.4 : Data Engineer


```http
GET offres/_search
{
  "size": 0,
  "query": {
    "match_phrase": {
      "titre": "Data Engineer"
    }
  },
  "aggs": {
    "top_competences": {
      "terms": {
        "field": "competences",
        "size": 5
      }
    },
    "teletravail_plus_frequent": {
      "terms": {
        "field": "teletravail",
        "size": 3
      }
    }
  }
}


```

# Exercice 4.5 : visualisation Kibana


# Réalisé dans Kibana Lens :

# Axe horizontal : ville

# Axe vertical : Count of records

# Breakdown : contrat

# Nombre de valeurs ville : 12

# Visualisation enregistrée : "Offres par ville et contrat"
