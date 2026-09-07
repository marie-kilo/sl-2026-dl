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

```powershell
```