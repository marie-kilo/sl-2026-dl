"""Teste MinIO et MongoDB avec les données réelles du fichier Parquet."""

from collections import defaultdict

import duckdb
from pymongo import MongoClient

from src.logger import (
    Timer,
    get_logger,
)
from src.utils.minio_client import (
    get_s3_client,
)

logger = get_logger(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

BUCKET_NAME = "test-data"
OBJECT_NAME = "tram_stops.parquet"

LOCAL_FILE = "/app/data/tram_stops.parquet"

DOWNLOADED_FILE = "/tmp/tram_stops_downloaded.parquet"

MONGO_DATABASE = "datalake"
MONGO_COLLECTION = "tram_routes"


# ============================================================
# TEST MINIO
# ============================================================


def test_minio():
    """Écrit puis relit le fichier Parquet dans MinIO."""
    logger.info("Début du test MinIO.")

    s3_client = get_s3_client()

    # ========================================================
    # CRÉATION DU BUCKET
    # ========================================================

    buckets = [bucket["Name"] for bucket in (s3_client.list_buckets()["Buckets"])]

    if BUCKET_NAME not in buckets:
        s3_client.create_bucket(Bucket=BUCKET_NAME)

        logger.info(
            "Bucket créé : %s",
            BUCKET_NAME,
        )

    else:
        logger.info(
            "Bucket déjà existant : %s",
            BUCKET_NAME,
        )

    # ========================================================
    # ÉCRITURE DANS MINIO
    # ========================================================

    s3_client.upload_file(
        LOCAL_FILE,
        BUCKET_NAME,
        OBJECT_NAME,
    )

    logger.info(
        "Fichier envoyé dans MinIO : %s/%s",
        BUCKET_NAME,
        OBJECT_NAME,
    )

    # ========================================================
    # VÉRIFICATION DES OBJETS
    # ========================================================

    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME)

    objects = response.get(
        "Contents",
        [],
    )

    logger.info(
        "Nombre d'objets dans le bucket : %s",
        len(objects),
    )

    for obj in objects:
        logger.info(
            "Objet présent : %s",
            obj["Key"],
        )

    # ========================================================
    # RELECTURE DEPUIS MINIO
    # ========================================================

    s3_client.download_file(
        BUCKET_NAME,
        OBJECT_NAME,
        DOWNLOADED_FILE,
    )

    logger.info(
        "Fichier relu depuis MinIO : %s",
        DOWNLOADED_FILE,
    )

    # ========================================================
    # LECTURE AVEC DUCKDB
    # ========================================================

    connection = duckdb.connect()

    try:
        rows = connection.execute(
            f"""
                SELECT *
                FROM read_parquet(
                    '{DOWNLOADED_FILE}'
                )
                LIMIT 5
                """
        ).fetchall()

        logger.info("5 premières lignes du Parquet :")

        for row in rows:
            logger.info(
                "%s",
                row,
            )

    finally:
        connection.close()

        logger.info("Connexion DuckDB fermée.")

    logger.info("Test MinIO terminé avec succès.")


# ============================================================
# CONSTRUCTION DES DOCUMENTS MONGODB
# ============================================================


def build_route_documents(
    parquet_file,
):
    """Construit un document MongoDB par ligne avec ses arrêts."""
    logger.info("Construction des documents MongoDB depuis le Parquet.")

    connection = duckdb.connect()

    try:
        rows = connection.execute(
            f"""
                SELECT DISTINCT
                    route_id,
                    route_short_name,
                    stop_id,
                    stop_name,
                    stop_lat,
                    stop_lon
                FROM read_parquet(
                    '{parquet_file}'
                )
                WHERE route_id IS NOT NULL
                  AND stop_id IS NOT NULL
                ORDER BY
                    route_id,
                    stop_id
                """
        ).fetchall()

    finally:
        connection.close()

        logger.info("Connexion DuckDB fermée.")

    logger.info(
        "%s lignes lues depuis le Parquet.",
        len(rows),
    )

    routes = defaultdict(
        lambda: {
            "route_short_name": None,
            "stops": [],
        }
    )

    for row in rows:
        (
            route_id,
            route_short_name,
            stop_id,
            stop_name,
            stop_lat,
            stop_lon,
        ) = row

        routes[route_id]["route_short_name"] = route_short_name

        routes[route_id]["stops"].append(
            {
                "stop_id": stop_id,
                "stop_name": stop_name,
                "stop_lat": stop_lat,
                "stop_lon": stop_lon,
            }
        )

    documents = []

    for (
        route_id,
        route_data,
    ) in routes.items():
        documents.append(
            {
                "route_id": route_id,
                "route_short_name": (route_data["route_short_name"]),
                "stops": (route_data["stops"]),
            }
        )

    logger.info(
        "%s documents MongoDB construits.",
        len(documents),
    )

    return documents


# ============================================================
# TEST MONGODB
# ============================================================


def test_mongodb():
    """Écrit, relit et agrège les données dans MongoDB."""
    logger.info("Début du test MongoDB.")

    from os import getenv

    mongo_host = getenv("MONGO_HOST")

    mongo_port = int(
        getenv(
            "MONGO_PORT",
            "27017",
        )
    )

    mongo_username = getenv("MONGO_USERNAME")

    mongo_password = getenv("MONGO_PASSWORD")

    mongo_database = getenv(
        "MONGO_DATABASE",
        MONGO_DATABASE,
    )

    client = MongoClient(
        host=mongo_host,
        port=mongo_port,
        username=mongo_username,
        password=mongo_password,
        authSource="admin",
    )

    try:
        # ====================================================
        # TEST DE CONNEXION
        # ====================================================

        client.admin.command("ping")

        logger.info("Connexion MongoDB réussie.")

        database = client[mongo_database]

        collection = database[MONGO_COLLECTION]

        # ====================================================
        # NETTOYAGE DU TEST PRÉCÉDENT
        # ====================================================

        deleted = collection.delete_many({})

        logger.info(
            "%s anciens documents supprimés.",
            deleted.deleted_count,
        )

        # ====================================================
        # CONSTRUCTION DES DOCUMENTS
        # ====================================================

        with Timer() as timer:
            documents = build_route_documents(DOWNLOADED_FILE)

        logger.info(
            "Construction des documents terminée en %.4f s.",
            timer.elapsed,
        )

        if not documents:
            logger.warning("Aucun document à insérer.")
            return

        # ====================================================
        # INSERTION
        # ====================================================

        result = collection.insert_many(documents)

        logger.info(
            "%s documents insérés dans MongoDB.",
            len(result.inserted_ids),
        )

        # ====================================================
        # RELECTURE
        # ====================================================

        document = collection.find_one(
            {},
            {
                "_id": 0,
            },
        )

        logger.info(
            "Exemple de document MongoDB : %s",
            document,
        )

        # ====================================================
        # AGRÉGATION MONGODB
        # ====================================================

        aggregation_pipeline = [
            {
                "$project": {
                    "_id": 0,
                    "route_id": 1,
                    "route_short_name": 1,
                    "number_of_stops": {
                        "$size": "$stops",
                    },
                }
            },
            {
                "$sort": {
                    "number_of_stops": -1,
                }
            },
            {
                "$limit": 10,
            },
        ]

        logger.info("Top 10 des lignes par nombre d'arrêts :")

        for result in collection.aggregate(aggregation_pipeline):
            logger.info(
                "%s",
                result,
            )

        logger.info("Test MongoDB terminé avec succès.")

    finally:
        client.close()

        logger.info("Connexion MongoDB fermée.")


# ============================================================
# MAIN
# ============================================================


def main():
    """Exécute les tests MinIO puis MongoDB."""
    logger.info("Démarrage de la Partie 1.")

    try:
        with Timer() as total_timer:
            with Timer() as timer:
                test_minio()

            logger.info(
                "Test MinIO exécuté en %.4f s.",
                timer.elapsed,
            )

            with Timer() as timer:
                test_mongodb()

            logger.info(
                "Test MongoDB exécuté en %.4f s.",
                timer.elapsed,
            )

        logger.info(
            "Partie 1 terminée avec succès en %.4f s.",
            total_timer.elapsed,
        )

    except Exception:
        logger.exception("La Partie 1 a échoué.")
        raise


if __name__ == "__main__":
    main()
