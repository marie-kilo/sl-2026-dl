"""Dépose le fichier Parquet brut dans la zone Raw de MinIO."""

import logging

from src.utils.minio_client import get_s3_client


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


RAW_BUCKET = "raw"
RAW_OBJECT = "tram/tram_stops.parquet"

LOCAL_FILE = "/app/data/tram_stops.parquet"


def ensure_bucket(
    s3_client,
    bucket_name,
):
    """Crée le bucket s'il n'existe pas."""
    buckets = [
        bucket["Name"]
        for bucket in s3_client.list_buckets()["Buckets"]
    ]

    if bucket_name not in buckets:
        s3_client.create_bucket(
            Bucket=bucket_name
        )

        logger.info(
            "Bucket créé : %s",
            bucket_name,
        )

    else:
        logger.info(
            "Bucket déjà existant : %s",
            bucket_name,
        )


def upload_raw_file():
    """Envoie le fichier Parquet brut dans MinIO Raw."""
    logger.info(
        "Début de l'ingestion Raw."
    )

    s3_client = get_s3_client()

    try:
        ensure_bucket(
            s3_client,
            RAW_BUCKET,
        )

        s3_client.upload_file(
            LOCAL_FILE,
            RAW_BUCKET,
            RAW_OBJECT,
        )

        logger.info(
            "Fichier envoyé : s3://%s/%s",
            RAW_BUCKET,
            RAW_OBJECT,
        )

        response = s3_client.head_object(
            Bucket=RAW_BUCKET,
            Key=RAW_OBJECT,
        )

        logger.info(
            "Taille du fichier : %s octets",
            response["ContentLength"],
        )

        logger.info(
            "Ingestion Raw terminée avec succès."
        )

    except Exception:
        logger.exception(
            "Erreur pendant l'ingestion Raw."
        )
        raise


def main():
    """Lance l'ingestion Raw."""
    upload_raw_file()


if __name__ == "__main__":
    main()