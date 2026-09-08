# Data Lake avec MinIO, DuckDB et MongoDB

## Présentation

Ce projet a été réalisé dans le cadre du brief **« Faire circuler des données entre des briques de stockage hétérogènes (S3 et MongoDB) »**.

L'objectif est de construire un petit pipeline de Data Lake conteneurisé dans lequel des données issues d'un fichier GTFS transitent entre plusieurs briques de stockage :

- **MinIO** pour le stockage objet compatible S3 ;
- **DuckDB** pour la lecture et la transformation des fichiers Parquet ;
- **MongoDB** pour le stockage des données sous forme de documents ;
- **Python** pour l'orchestration du pipeline ;
- **Docker Compose** pour exécuter et faire communiquer les différents services.

Le projet est réalisé en deux parties :

1. découverte et test de MinIO et MongoDB ;
2. construction d'un pipeline complet organisé en zones `raw` et `curated`.

---

# 1. Architecture

Le pipeline principal suit le chemin suivant :

```text
GTFS / Parquet
      |
      v
+-------------+
|  Ingestion  |
+-------------+
      |
      v
+------------------+
| MinIO            |
| bucket : raw     |
+------------------+
      |
      v
+------------------+
| Processing       |
| DuckDB           |
+------------------+
      |
      v
+------------------+
| MinIO            |
| bucket : curated |
+------------------+
      |
      v
+------------------+
| Loading          |
+------------------+
      |
      v
+------------------+
| MongoDB          |
| datalake         |
| tram_routes      |
+------------------+
```

Les conteneurs communiquent entre eux grâce au réseau Docker Compose.

À l'intérieur du réseau Docker, les services sont appelés par leur **nom de service** et non avec `localhost`.

Exemples :

```text
http://minio:9000
mongodb:27017
```

---

# 2. Technologies utilisées

- Python
- Docker
- Docker Compose
- MinIO
- boto3
- DuckDB
- MongoDB
- pymongo
- Parquet
- Ruff
- pytest

---

# 3. Organisation du projet

```text
sl-2026-dl/
│
├── data/
│
├── docker/
│   ├── docker-compose.yml
│   └── Dockerfile
│
├── logs/
│   └── journal.log
│
├── src/
│   ├── config/
│   │   └── settings.py
│   │
│   ├── ingestion/
│   │   └── ingest_raw.py
│   │
│   ├── loading/
│   │   └── load_mongodb.py
│   │
│   ├── part1/
│   │   ├── __init__.py
│   │   └── test_storage.py
│   │
│   ├── processing/
│   │   └── transform_curated.py
│   │
│   ├── utils/
│   │   ├── minio_client.py
│   │   └── mongo_client.py
│   │
│   ├── logger.py
│   ├── main.py
│   ├── test.py
│   └── test_funk.py
│
├── tests/
│   ├── __init__.py
│   ├── test_loading.py
│   └── test_processing.py
│
├── .env
├── .env.example
├── .gitignore
├── pyproject.toml
├── requirements.txt
└── README.md
```

> Le dossier `logs/`, le fichier `.env`, les environnements virtuels et les fichiers Python compilés sont ignorés par Git.

---

# 4. Configuration

## 4.1 Variables d'environnement

Les identifiants et secrets ne sont pas écrits directement dans le code.

Créer un fichier `.env` à partir de `.env.example`.

Exemple :

```env
MINIO_ENDPOINT=http://minio:9000
MINIO_ACCESS_KEY=minio
MINIO_SECRET_KEY=minio123

MONGO_HOST=mongodb
MONGO_PORT=27017
MONGO_USERNAME=username
MONGO_PASSWORD=password
MONGO_DATABASE=datalake
```

Le fichier `.env` est ignoré par Git.

Le fichier `.env.example` permet de documenter les variables nécessaires sans publier les secrets utilisés localement.

---

# 5. Lancement de l'environnement

Depuis la racine du projet :

```powershell
docker compose -f docker/docker-compose.yml `
  --env-file .env `
  up -d minio mongodb
```

Vérifier l'état des services :

```powershell
docker compose -f docker/docker-compose.yml `
  --env-file .env `
  ps -a
```

MinIO et MongoDB disposent de healthchecks afin de vérifier leur disponibilité avant l'exécution du pipeline.

---

# 6. Partie 1 — Découverte de MinIO et MongoDB

La première partie permet de tester indépendamment les deux systèmes de stockage.

Le programme correspondant se trouve dans :

```text
src/part1/test_storage.py
```

## MinIO

Le programme :

1. se connecte à MinIO avec `boto3` ;
2. crée ou vérifie le bucket `test-data` ;
3. dépose un fichier Parquet ;
4. liste les objets du bucket ;
5. télécharge le fichier ;
6. relit le fichier avec DuckDB.

## MongoDB

Le programme :

1. se connecte à MongoDB avec `pymongo` ;
2. construit des documents à partir du Parquet ;
3. crée un document par ligne de transport ;
4. imbrique directement les arrêts dans le document parent ;
5. insère les documents dans MongoDB ;
6. exécute une agrégation permettant notamment de classer les lignes selon leur nombre d'arrêts.

Exemple simplifié d'un document :

```json
{
  "route_id": "IDFM:C00563",
  "route_short_name": "CDG VAL",
  "stops": [
    {
      "stop_id": "IDFM:10214",
      "stop_name": "Parking Pr",
      "stop_lat": 49.0089,
      "stop_lon": 2.5448
    }
  ]
}
```

Cette structure exploite le modèle documentaire de MongoDB : les arrêts sont directement imbriqués dans leur route au lieu d'effectuer une jointure à chaque lecture.

## Exécution de la Partie 1

```powershell
docker compose -f docker/docker-compose.yml `
  --env-file .env `
  run --rm pipeline `
  python -m src.part1.test_storage
```

---

# 7. Partie 2 — Pipeline Data Lake

La Partie 2 met en place le pipeline complet :

```text
GTFS
  ↓
Ingestion
  ↓
MinIO / raw
  ↓
DuckDB
  ↓
MinIO / curated
  ↓
Loading
  ↓
MongoDB
```

## Étape 1 — Ingestion

Le fichier :

```text
src/ingestion/ingest_raw.py
```

dépose le fichier Parquet brut dans MinIO.

Destination :

```text
s3://raw/tram/tram_stops.parquet
```

Cette zone conserve les données brutes.

---

## Étape 2 — Transformation

Le fichier :

```text
src/processing/transform_curated.py
```

récupère le fichier de la zone `raw` et utilise DuckDB pour effectuer le traitement.

Le traitement vérifie/nettoie notamment les données nécessaires avant leur stockage dans la zone `curated`.

Le résultat est écrit dans :

```text
s3://curated/tram/tram_stops_clean.parquet
```

Lors de l'exécution actuelle :

```text
Nombre de lignes Raw     : 580
Nombre de lignes Curated : 580
Nombre de lignes supprimées : 0
```

Les 580 lignes du fichier utilisé respectent donc les règles de nettoyage appliquées.

---

## Étape 3 — Chargement dans MongoDB

Le fichier :

```text
src/loading/load_mongodb.py
```

lit le fichier Curated puis construit les documents MongoDB.

Les données sont stockées dans :

```text
Base       : datalake
Collection : tram_routes
```

Le pipeline construit actuellement :

```text
17 documents MongoDB
```

Chaque document représente une route et contient directement la liste de ses arrêts.

---

# 8. Point d'entrée principal

Le fichier :

```text
src/main.py
```

est le point d'entrée de la **Partie 2**.

Il orchestre successivement :

```text
ingestion
    ↓
transformation
    ↓
chargement MongoDB
```

La Partie 1 reste volontairement séparée car elle correspond aux tests de découverte demandés dans la première partie du brief.

## Exécution du pipeline complet

```powershell
docker compose -f docker/docker-compose.yml `
  --env-file .env `
  run --rm pipeline `
  python -m src.main
```

Une exécution correcte se termine par un log similaire à :

```text
Pipeline terminé avec succès
```

---

# 9. Vérification de MinIO

Depuis la machine hôte, l'interface MinIO est accessible sur :

```text
http://localhost:9001
http://localhost:9001/browser/raw
http://localhost:9001/browser/curated
http://localhost:9001/browser/test-data
```

Il est également possible de vérifier les buckets avec le client `mc`.

Configuration de l'alias :

```powershell
docker exec minio mc alias set local http://localhost:9000 minio minio123
```

Liste des buckets :

```powershell
docker exec minio mc ls local
```

Les buckets utilisés sont notamment :

```text
raw/
curated/
test-data/
```

Vérifier la zone Raw :

```powershell
docker exec minio mc ls --recursive local/raw
```

Résultat attendu :

```text
tram/tram_stops.parquet
```

Vérifier la zone Curated :

```powershell
docker exec minio mc ls --recursive local/curated
```

Résultat attendu :

```text
tram/tram_stops_clean.parquet
```

---

# 10. Vérification de MongoDB

Ouvrir le shell MongoDB :

```powershell
docker exec -it mongodb mongosh `
  -u username `
  -p password `
  --authenticationDatabase admin
```

Puis :

```javascript
use datalake
```

Afficher les collections :

```javascript
show collections
```

La collection principale du pipeline est :

```text
tram_routes
```

Compter les documents :

```javascript
db.tram_routes.countDocuments()
```

Résultat avec les données actuelles :

```text
17
```

Afficher un document :

```javascript
db.tram_routes.findOne()
```

Ou plusieurs documents :

```javascript
db.tram_routes.find().limit(3).pretty()
```

---

# 11. Logging

Le projet utilise le module standard `logging` de Python.

La configuration commune se trouve dans :

```text
src/logger.py
```

Les logs contiennent notamment :

- la date et l'heure ;
- le niveau (`INFO`, `WARNING`, `ERROR`, etc.) ;
- le fichier ;
- le numéro de ligne ;
- le nom de la fonction ;
- le message.

Exemple :

```text
2026-09-08 07:48:42,803 INFO main.py :0013 main Démarrage du pipeline.
```

Les logs sont affichés dans la console avec une coloration selon le niveau et sont également enregistrés dans :

```text
logs/journal.log
```

Le temps d'exécution des principales étapes est mesuré proprement grâce à la classe `Timer`.

Exemple :

```text
Ingestion Raw terminée avec succès en 0.1575 s.
Transformation DuckDB exécutée en 0.0478 s.
Chargement MongoDB exécuté en 0.0662 s.
Pipeline terminé avec succès en 0.4287 s.
```

Pour afficher les 30 dernières lignes du journal :

```powershell
Get-Content .\logs\journal.log -Encoding UTF8 -Tail 30
```

---

# 12. Qualité du code avec Ruff

Le projet utilise Ruff pour le linting et le formatage du code Python.

La configuration se trouve dans :

```text
pyproject.toml
```

## Vérifier tout le projet

```powershell
docker compose -f docker/docker-compose.yml `
  --env-file .env `
  run --rm pipeline `
  ruff check /app --config /app/pyproject.toml
```

Résultat attendu :

```text
All checks passed!
```

## Vérifier le formatage

```powershell
docker compose -f docker/docker-compose.yml `
  --env-file .env `
  run --rm pipeline `
  ruff format /app --check --config /app/pyproject.toml
```

Si Ruff détecte des fichiers non formatés :

```powershell
docker compose -f docker/docker-compose.yml `
  --env-file .env `
  run --rm pipeline `
  ruff format /app --config /app/pyproject.toml
```

---

# 13. Tests automatisés

Des tests automatisés ont été ajoutés avec `pytest`.

Ils se trouvent dans :

```text
tests/
├── test_loading.py
└── test_processing.py
```

## Test du processing

`test_processing.py` vérifie la logique de nettoyage Raw → Curated à partir d'un petit jeu de données de test.

Il vérifie notamment qu'une ligne invalide est supprimée.

## Test du loading

`test_loading.py` vérifie la construction de la structure documentaire utilisée pour MongoDB.

Il vérifie notamment :

- la création d'une route ;
- son identifiant ;
- son nom ;
- l'imbrication des arrêts ;
- le nombre d'arrêts.

## Lancer les tests

```powershell
docker compose -f docker/docker-compose.yml `
  --env-file .env `
  run --rm pipeline `
  pytest /app/tests -v
```

Résultat obtenu :

```text
collected 2 items

tests/test_loading.py::test_build_documents PASSED
tests/test_processing.py::test_cleaning_rules PASSED
```

Les deux tests passent correctement.

---

# 14. Arrêter les services

Pour arrêter l'environnement :

```powershell
docker compose -f docker/docker-compose.yml `
  --env-file .env `
  down
```

Pour supprimer également les volumes Docker :

```powershell
docker compose -f docker/docker-compose.yml `
  --env-file .env `
  down -v
```

Attention : `-v` supprime les données persistées dans les volumes Docker.

---

# 15. Bonnes pratiques appliquées

Le projet applique plusieurs bonnes pratiques demandées dans le brief :

- code organisé dans un package `src/` ;
- utilisation de Docker Compose ;
- communication entre conteneurs par leur nom de service ;
- variables d'environnement pour les identifiants et secrets ;
- fichier `.env` ignoré par Git ;
- fichier `.env.example` fourni ;
- séparation des zones `raw` et `curated` ;
- stockage objet avec MinIO ;
- traitement Parquet avec DuckDB ;
- stockage documentaire avec MongoDB ;
- documents MongoDB imbriqués ;
- connexions DuckDB et MongoDB correctement fermées ;
- healthchecks Docker ;
- logging centralisé ;
- logs enregistrés dans un fichier ;
- chronométrage des traitements ;
- contrôle du code avec Ruff ;
- tests automatisés avec pytest.

---

# 16. Questions ouvertes

## Pourquoi faire transiter la donnée par le stockage objet plutôt que d'aller directement de GTFS à MongoDB ?

Le passage par un stockage objet permet de **découpler les différentes étapes du pipeline**.

Si les données étaient envoyées directement de la source GTFS vers MongoDB, le chargement et le traitement seraient fortement liés. En cas d'erreur dans MongoDB ou dans la transformation, il pourrait être nécessaire de récupérer de nouveau les données depuis la source.

Avec MinIO, le fichier brut est conservé indépendamment dans la zone `raw`.

Cela apporte plusieurs avantages :

- conservation d'une copie des données sources ;
- possibilité de rejouer le traitement ;
- découplage entre ingestion, transformation et chargement ;
- facilité de diagnostic en cas d'erreur ;
- possibilité d'utiliser ultérieurement les mêmes fichiers pour d'autres traitements ou systèmes de stockage.

Le stockage objet est également particulièrement adapté aux fichiers tels que Parquet et permet de se rapprocher de l'architecture d'un Data Lake utilisant un stockage S3 dans le cloud.

---

## À quoi servent les deux zones `raw` et `curated` ? Pourquoi ne pas en avoir une seule ?

Les deux zones correspondent à deux états différents de la donnée.

### Zone Raw

La zone `raw` contient la donnée dans son état brut, aussi proche que possible de la source.

Dans ce projet :

```text
s3://raw/tram/tram_stops.parquet
```

Cette zone permet notamment de :

- conserver la donnée originale ;
- disposer d'un historique ou d'une référence ;
- rejouer les transformations ;
- diagnostiquer une erreur de traitement.

### Zone Curated

La zone `curated` contient une version préparée et nettoyée des données.

Dans ce projet :

```text
s3://curated/tram/tram_stops_clean.parquet
```

Cette zone contient les données prêtes pour les traitements ou le chargement dans MongoDB.

Séparer les deux zones évite donc d'écraser les données sources lors du nettoyage.

L'architecture devient :

```text
Source
   ↓
RAW
   ↓
Nettoyage / transformation
   ↓
CURATED
   ↓
MongoDB
```

Avec une seule zone, les données brutes et transformées seraient mélangées ou les données originales risqueraient d'être remplacées. La séparation `raw` / `curated` améliore donc la traçabilité, la reproductibilité et la maintenabilité du pipeline.

---

# 17. Résumé de l'exécution

Pour reproduire rapidement le projet :

### 1. Démarrer MinIO et MongoDB

```powershell
docker compose -f docker/docker-compose.yml `
  --env-file .env `
  up -d minio mongodb
```

### 2. Exécuter la Partie 1

```powershell
docker compose -f docker/docker-compose.yml `
  --env-file .env `
  run --rm pipeline `
  python -m src.part1.test_storage
```

### 3. Exécuter le pipeline de la Partie 2

```powershell
docker compose -f docker/docker-compose.yml `
  --env-file .env `
  run --rm pipeline `
  python -m src.main
```

### 4. Lancer les tests

```powershell
docker compose -f docker/docker-compose.yml `
  --env-file .env `
  run --rm pipeline `
  pytest /app/tests -v
```

### 5. Vérifier Ruff

```powershell
docker compose -f docker/docker-compose.yml `
  --env-file .env `
  run --rm pipeline `
  ruff check /app --config /app/pyproject.toml
```

```powershell
docker compose -f docker/docker-compose.yml `
  --env-file .env `
  run --rm pipeline `
  ruff format /app --check --config /app/pyproject.toml
```

À la dernière vérification :

```text
All checks passed!
```

et :

```text
tests/test_loading.py::test_build_documents PASSED
tests/test_processing.py::test_cleaning_rules PASSED
```