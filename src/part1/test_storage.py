"""Teste MinIO et MongoDB avec les données réelles du fichier Parquet."""

import logging
import os
from collections import defaultdict

import boto3
import duckdb
from botocore.client import Config
from pymongo import MongoClient


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")

MONGO_HOST = os.getenv("MONGO_HOST")
MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))
MONGO_USERNAME = os.getenv("MONGO_USERNAME")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_DATABASE = os.getenv("MONGO_DATABASE")

BUCKET_NAME = "test-data"
OBJECT_NAME = "tram_stops.parquet"

LOCAL_FILE = "/app/data/tram_stops.parquet"
DOWNLOADED_FILE = "/tmp/tram_stops_downloaded.parquet"


# ============================================================
# CLIENT MINIO
# ============================================================


def get_s3_client():
    """Crée le client S3 utilisé pour communiquer avec MinIO."""
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


# ============================================================
# TEST MINIO
# ============================================================


def test_minio():
    """Écrit puis relit le fichier Parquet dans MinIO."""
    logger.info("Début du test MinIO.")

    s3 = get_s3_client()

    try:
        buckets = [
            bucket["Name"]
            for bucket in s3.list_buckets()["Buckets"]
        ]

        if BUCKET_NAME not in buckets:
            s3.create_bucket(
                Bucket=BUCKET_NAME
            )

            logger.info(
                "Bucket créé : %s",
                BUCKET_NAME,
            )

        else:
            logger.info(
                "Bucket déjà existant : %s",
                BUCKET_NAME,
            )

        # Envoi du fichier Parquet dans MinIO.
        s3.upload_file(
            LOCAL_FILE,
            BUCKET_NAME,
            OBJECT_NAME,
        )

        logger.info(
            "Fichier envoyé dans MinIO : %s/%s",
            BUCKET_NAME,
            OBJECT_NAME,
        )

        # Vérification des objets présents.
        response = s3.list_objects_v2(
            Bucket=BUCKET_NAME
        )

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

        # Relecture depuis MinIO.
        s3.download_file(
            BUCKET_NAME,
            OBJECT_NAME,
            DOWNLOADED_FILE,
        )

        logger.info(
            "Fichier relu depuis MinIO : %s",
            DOWNLOADED_FILE,
        )

        # Vérification avec DuckDB.
        connection = duckdb.connect()

        try:
            rows = connection.execute(
                """
                SELECT *
                FROM read_parquet(?)
                LIMIT 5
                """,
                [DOWNLOADED_FILE],
            ).fetchall()

            logger.info(
                "5 premières lignes du Parquet :"
            )

            for row in rows:
                logger.info(
                    "%s",
                    row,
                )

        finally:
            connection.close()

        logger.info(
            "Test MinIO terminé avec succès."
        )

    except Exception:
        logger.exception(
            "Erreur pendant le test MinIO."
        )
        raise


# ============================================================
# CONSTRUCTION DES DOCUMENTS MONGODB
# ============================================================


def build_route_documents(
    parquet_file,
):
    """Construit un document MongoDB par ligne avec ses arrêts."""
    logger.info(
        "Construction des documents MongoDB depuis le Parquet."
    )

    connection = duckdb.connect()

    try:
        rows = connection.execute(
            """
            SELECT DISTINCT
                route_id,
                route_short_name,
                stop_id,
                stop_name,
                stop_lat,
                stop_lon
            FROM read_parquet(?)
            WHERE route_id IS NOT NULL
              AND stop_id IS NOT NULL
            ORDER BY
                route_id,
                stop_id
            """,
            [parquet_file],
        ).fetchall()

    finally:
        connection.close()

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

        routes[route_id][
            "route_short_name"
        ] = route_short_name

        routes[route_id][
            "stops"
        ].append(
            {
                "stop_id": stop_id,
                "stop_name": stop_name,
                "stop_lat": stop_lat,
                "stop_lon": stop_lon,
            }
        )

    documents = []

    for route_id, route_data in routes.items():
        documents.append(
            {
                "route_id": route_id,
                "route_short_name": (
                    route_data[
                        "route_short_name"
                    ]
                ),
                "stops": route_data["stops"],
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
    logger.info(
        "Début du test MongoDB."
    )

    client = MongoClient(
        host=MONGO_HOST,
        port=MONGO_PORT,
        username=MONGO_USERNAME,
        password=MONGO_PASSWORD,
        authSource="admin",
    )

    try:
        client.admin.command(
            "ping"
        )

        logger.info(
            "Connexion MongoDB réussie."
        )

        database = client[
            MONGO_DATABASE
        ]

        collection = database[
            "tram_routes"
        ]

        # Nettoyage d'un test précédent.
        deleted = collection.delete_many(
            {}
        )

        logger.info(
            "%s anciens documents supprimés.",
            deleted.deleted_count,
        )

        # Création des documents à partir
        # du fichier relu depuis MinIO.
        documents = build_route_documents(
            DOWNLOADED_FILE
        )

        if not documents:
            logger.warning(
                "Aucun document à insérer."
            )
            return

        result = collection.insert_many(
            documents
        )

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
        # AGRÉGATION
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

        logger.info(
            "Top 10 des lignes par nombre d'arrêts :"
        )

        for result in collection.aggregate(
            aggregation_pipeline
        ):
            logger.info(
                "%s",
                result,
            )

        logger.info(
            "Test MongoDB terminé avec succès."
        )

    except Exception:
        logger.exception(
            "Erreur pendant le test MongoDB."
        )
        raise

    finally:
        client.close()

        logger.info(
            "Connexion MongoDB fermée."
        )


# ============================================================
# MAIN
# ============================================================


def main():
    """Exécute les tests MinIO puis MongoDB."""
    logger.info(
        "Démarrage de la Partie 1."
    )

    try:
        test_minio()
        test_mongodb()

        logger.info(
            "Partie 1 terminée avec succès."
        )

    except Exception:
        logger.exception(
            "La Partie 1 a échoué."
        )
        raise


if __name__ == "__main__":
    main()