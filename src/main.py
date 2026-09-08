"""Point d'entrée principal du pipeline."""

from src.ingestion.ingest_raw import main as ingestion_main
from src.loading.load_mongodb import main as loading_main
from src.logger import Timer, get_logger
from src.processing.transform_curated import main as processing_main

logger = get_logger(__name__)


def main():
    """Exécute le pipeline complet."""
    logger.info("Démarrage du pipeline.")

    with Timer() as timer:
        ingestion_main()
        logger.info("Étape ingestion terminée avec succès.")

        processing_main()
        logger.info("Étape processing terminée avec succès.")

        loading_main()
        logger.info("Étape loading terminée avec succès.")

    logger.info(
        "Pipeline terminé avec succès en %.4f s.",
        timer.elapsed,
    )


if __name__ == "__main__":
    main()
