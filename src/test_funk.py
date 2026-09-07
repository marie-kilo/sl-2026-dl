"""Fonctions utilisées pour la démonstration du logging."""

from src.logger import get_logger

logger = get_logger(__name__)


def my_amazing_funk():
    """Fonction de démonstration sans traitement particulier."""
    return


def other_func():
    """Écrit un message dans les logs."""
    logger.info("other func")
