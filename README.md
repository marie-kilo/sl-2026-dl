```powershell
docker compose -f docker/docker-compose.yml --env-file .env build

docker compose -f docker/docker-compose.yml --env-file .env up -d

docker compose -f docker/docker-compose.yml --env-file .env ps
```

* Pour vérifier que les librairies Python sont bien installées dans le conteneur pipeline :
```powershell
docker compose -f docker/docker-compose.yml --env-file .env run --rm pipeline python -c "import boto3, duckdb, pymongo, pyarrow; print('Imports OK')"
```

* Et pour vérifier la version de boto3 :
```powershell
docker compose -f docker/docker-compose.yml --env-file .env run --rm pipeline python -c "import boto3; print(boto3.__version__)"
```

* après creation le fichier test_storage dans la partie 1:
```powershell
docker compose -f docker/docker-compose.yml --env-file .env up --build pipeline
```
* ou plus simple:
```powershell
docker compose -f docker/docker-compose.yml `
  --env-file .env `
  run --name part1-test pipeline
```
* Et pour consulter ensuite les logs d’un conteneur lancé via up
```powershell
docker logs part1-test
```
## Partie 2:

```powershell
docker compose -f docker/docker-compose.yml `
  --env-file .env `
  build ingestion
```
* puis:

```powershell
docker compose -f docker/docker-compose.yml `
  --env-file .env `
  run --rm ingestion
```


```powershell
docker compose -f docker/docker-compose.yml `
  --env-file .env `
  build processing
```

```powershell
docker compose -f docker/docker-compose.yml `
  --env-file .env `
  run --rm processing
```

```powershell
docker compose -f docker/docker-compose.yml `
  --env-file .env `
  build loading
```

```powershell
docker compose -f docker/docker-compose.yml `
  --env-file .env `
  run --rm loading
```
* pour vérifier le pipeline:

```powershell

docker compose -f docker/docker-compose.yml `
  --env-file .env `
  ps -a
```


```powershell
docker compose -f docker/docker-compose.yml `
  --env-file .env `
  up --build
```


* vérifier MINIO:
- dans la navigateur: 
**http://localhost:9001/browser/raw***
***http://localhost:9001/browser/curated***
***http://localhost:9001/browser/test-data ***

```powershell
docker exec minio mc alias set local http://localhost:9000 minio minio123
```

```powershell
docker exec minio mc ls local/raw
```

```powershell
docker exec minio mc ls local/raw/tram
```

```powershell
docker exec minio mc ls local/curated
```

```powershell
docker exec minio mc ls local/curated/tram
```
* Pour vérifier MongoDB:

```powershell
docker exec -it mongodb mongosh `
  --username admin `
  --password admin123 `
  --authenticationDatabase admin
```

```powershell
use datalake
```

```powershell
show collections
```

```javascript
db.tram_routes.countDocuments()
```

```javascript
db.tram_routes.findOne()
```

```javascript
db.tram_routes.find().limit(3).pretty()
```
* ruff vérification:

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