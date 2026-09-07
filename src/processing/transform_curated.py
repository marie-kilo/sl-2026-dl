"""Lit les données Raw, les nettoie avec DuckDB et écrit la zone Curated."""

import logging

import duckdb

from src.utils.minio_client import get_s3_client


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

RAW_BUCKET = "raw"
RAW_OBJECT = "tram/tram_stops.parquet"

CURATED_BUCKET = "curated"
CURATED_OBJECT = "tram/tram_stops_clean.parquet"

RAW_LOCAL_FILE = "/tmp/tram_stops_raw.parquet"
CURATED_LOCAL_FILE = "/tmp/tram_stops_clean.parquet"


# ============================================================
# GESTION DES BUCKETS
# ============================================================


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


# ============================================================
# LECTURE RAW
# ============================================================


def download_raw_file(
    s3_client,
):
    """Télécharge le fichier Raw depuis MinIO."""
    logger.info(
        "Lecture du fichier Raw depuis MinIO."
    )

    s3_client.download_file(
        RAW_BUCKET,
        RAW_OBJECT,
        RAW_LOCAL_FILE,
    )

    logger.info(
        "Fichier Raw téléchargé : %s",
        RAW_LOCAL_FILE,
    )


# ============================================================
# TRANSFORMATION DUCKDB
# ============================================================


def transform_with_duckdb():
    """Nettoie le fichier Raw avec DuckDB."""
    logger.info(
        "Début de la transformation DuckDB."
    )

    connection = duckdb.connect()

    try:
        # ====================================================
        # NOMBRE DE LIGNES AVANT NETTOYAGE
        # ====================================================

        raw_count = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM read_parquet('{RAW_LOCAL_FILE}')
            """
        ).fetchone()[0]

        logger.info(
            "Nombre de lignes Raw : %s",
            raw_count,
        )

        # ====================================================
        # NETTOYAGE
        # ====================================================
        #
        # Les traitements appliqués sont :
        # - suppression des doublons avec DISTINCT ;
        # - suppression des route_id NULL ;
        # - suppression des stop_id NULL ;
        # - suppression des stop_name NULL ;
        # - contrôle des latitudes ;
        # - contrôle des longitudes.
        #
        # Le résultat est écrit dans un nouveau fichier
        # Parquet local avant son envoi dans MinIO Curated.
        # ====================================================

        connection.execute(
            f"""
            COPY (
                SELECT DISTINCT
                    route_id,
                    route_short_name,
                    stop_id,
                    stop_name,
                    stop_lat,
                    stop_lon
                FROM read_parquet('{RAW_LOCAL_FILE}')
                WHERE route_id IS NOT NULL
                  AND stop_id IS NOT NULL
                  AND stop_name IS NOT NULL
                  AND stop_lat BETWEEN -90 AND 90
                  AND stop_lon BETWEEN -180 AND 180
            )
            TO '{CURATED_LOCAL_FILE}'
            (FORMAT PARQUET)
            """
        )

        # ====================================================
        # NOMBRE DE LIGNES APRÈS NETTOYAGE
        # ====================================================

        curated_count = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM read_parquet('{CURATED_LOCAL_FILE}')
            """
        ).fetchone()[0]

        logger.info(
            "Nombre de lignes Curated : %s",
            curated_count,
        )

        logger.info(
            "Nombre de lignes supprimées : %s",
            raw_count - curated_count,
        )

        # ====================================================
        # CONTRÔLE DES DONNÉES CURATED
        # ====================================================

        rows = connection.execute(
            f"""
            SELECT *
            FROM read_parquet('{CURATED_LOCAL_FILE}')
            LIMIT 5
            """
        ).fetchall()

        logger.info(
            "5 premières lignes Curated :"
        )

        for row in rows:
            logger.info(
                "%s",
                row,
            )

    finally:
        connection.close()

        logger.info(
            "Connexion DuckDB fermée."
        )

    logger.info(
        "Transformation DuckDB terminée."
    )


# ============================================================
# ÉCRITURE CURATED
# ============================================================


def upload_curated_file(
    s3_client,
):
    """Envoie le fichier nettoyé dans MinIO Curated."""
    logger.info(
        "Début de l'écriture dans MinIO Curated."
    )

    ensure_bucket(
        s3_client,
        CURATED_BUCKET,
    )

    s3_client.upload_file(
        CURATED_LOCAL_FILE,
        CURATED_BUCKET,
        CURATED_OBJECT,
    )

    logger.info(
        "Fichier Curated envoyé : s3://%s/%s",
        CURATED_BUCKET,
        CURATED_OBJECT,
    )

    # Vérification de la présence du fichier.
    response = s3_client.head_object(
        Bucket=CURATED_BUCKET,
        Key=CURATED_OBJECT,
    )

    logger.info(
        "Taille du fichier Curated : %s octets",
        response["ContentLength"],
    )


# ============================================================
# MAIN
# ============================================================


def main():
    """Exécute le traitement Raw vers Curated."""
    logger.info(
        "Démarrage du traitement Raw -> Curated."
    )

    s3_client = get_s3_client()

    try:
        # 1. Lecture du Parquet brut depuis MinIO.
        download_raw_file(
            s3_client
        )

        # 2. Nettoyage avec DuckDB.
        transform_with_duckdb()

        # 3. Écriture du résultat dans MinIO Curated.
        upload_curated_file(
            s3_client
        )

        logger.info(
            "Traitement Raw -> Curated terminé avec succès."
        )

    except Exception:
        logger.exception(
            "Erreur pendant le traitement Raw -> Curated."
        )
        raise


if __name__ == "__main__":
    main()