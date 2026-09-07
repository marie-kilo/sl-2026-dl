"""Charge les données Curated dans MongoDB."""

import os
from collections import defaultdict

import duckdb
from pymongo import MongoClient

from src.config.settings import (
    CURATED_BUCKET,
    CURATED_OBJECT,
)
from src.logger import (
    Timer,
    get_logger,
)
from src.utils.minio_client import (
    get_s3_client,
)

logger = get_logger(__name__)


CURATED_LOCAL_FILE = "/tmp/tram_stops_clean.parquet"


MONGO_HOST = os.getenv("MONGO_HOST")

MONGO_PORT = int(
    os.getenv(
        "MONGO_PORT",
        "27017",
    )
)

MONGO_USERNAME = os.getenv("MONGO_USERNAME")

MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")

MONGO_DATABASE = os.getenv("MONGO_DATABASE")

COLLECTION_NAME = "tram_routes"


def download_curated_file(
    s3_client,
):
    """Télécharge le fichier Curated depuis MinIO."""
    logger.info("Lecture du fichier Curated depuis MinIO.")

    s3_client.download_file(
        CURATED_BUCKET,
        CURATED_OBJECT,
        CURATED_LOCAL_FILE,
    )

    logger.info(
        "Fichier Curated téléchargé : %s",
        CURATED_LOCAL_FILE,
    )


def build_route_documents():
    """Construit un document MongoDB par route."""
    logger.info("Construction des documents MongoDB depuis Curated.")

    connection = duckdb.connect()

    try:
        rows = connection.execute(
            f"""
                SELECT
                    route_id,
                    route_short_name,
                    stop_id,
                    stop_name,
                    stop_lat,
                    stop_lon
                FROM read_parquet(
                    '{CURATED_LOCAL_FILE}'
                )
                ORDER BY
                    route_id,
                    stop_id
                """
        ).fetchall()

    finally:
        connection.close()

        logger.info("Connexion DuckDB fermée.")

    logger.info(
        "%s lignes Curated lues.",
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


def load_to_mongodb(
    documents,
):
    """Insère les documents dans MongoDB."""
    client = MongoClient(
        host=MONGO_HOST,
        port=MONGO_PORT,
        username=MONGO_USERNAME,
        password=MONGO_PASSWORD,
        authSource="admin",
    )

    try:
        client.admin.command("ping")

        logger.info("Connexion MongoDB réussie.")

        database = client[MONGO_DATABASE]

        collection = database[COLLECTION_NAME]

        deleted = collection.delete_many({})

        logger.info(
            "%s anciens documents supprimés.",
            deleted.deleted_count,
        )

        if not documents:
            logger.warning("Aucun document à insérer.")
            return

        result = collection.insert_many(documents)

        logger.info(
            "%s documents insérés dans MongoDB.",
            len(result.inserted_ids),
        )

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

    finally:
        client.close()

        logger.info("Connexion MongoDB fermée.")


def main():
    """Exécute le chargement Curated vers MongoDB."""
    logger.info("Démarrage du chargement Curated -> MongoDB.")

    s3_client = get_s3_client()

    try:
        with Timer() as total_timer:
            download_curated_file(s3_client)

            with Timer() as timer:
                documents = build_route_documents()

            logger.info(
                "Construction des documents exécutée en %.4f s.",
                timer.elapsed,
            )

            with Timer() as timer:
                load_to_mongodb(documents)

            logger.info(
                "Chargement MongoDB exécuté en %.4f s.",
                timer.elapsed,
            )

        logger.info(
            "Chargement Curated -> MongoDB terminé avec succès en %.4f s.",
            total_timer.elapsed,
        )

    except Exception:
        logger.exception("Erreur pendant le chargement Curated -> MongoDB.")
        raise


if __name__ == "__main__":
    main()
