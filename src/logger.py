"""Configuration commune du logging et mesure des temps d'exécution."""

import logging
import os
import time
from typing import ClassVar

LOG_DIRECTORY = "/app/logs"
LOG_FILE = os.path.join(LOG_DIRECTORY, "journal.log")

LOG_FORMAT = (
    "%(asctime)s %(levelname)-8s %(filename)-16.16s:%(lineno)-4.4d %(funcName)-18.18s %(message)s"
)


class ColorFormatter(logging.Formatter):
    """Ajoute des couleurs aux niveaux de logs dans la console."""

    RESET = "\033[0m"

    COLORS: ClassVar[dict[int, str]] = {
        logging.DEBUG: "\033[36m",
        logging.INFO: "\033[32m",
        logging.WARNING: "\033[33m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[35m",
    }

    def format(self, record):
        """Formate un log en ajoutant une couleur selon son niveau."""
        color = self.COLORS.get(
            record.levelno,
            self.RESET,
        )

        message = super().format(record)

        return f"{color}{message}{self.RESET}"


def configure_logging():
    """Configure les logs console et fichier."""
    root_logger = logging.getLogger()

    if root_logger.handlers:
        return

    root_logger.setLevel(logging.INFO)

    # ========================================================
    # LOGS CONSOLE AVEC COULEURS
    # ========================================================

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    console_handler.setFormatter(ColorFormatter(LOG_FORMAT))

    root_logger.addHandler(console_handler)

    # ========================================================
    # LOGS DANS UN FICHIER
    # ========================================================

    os.makedirs(
        LOG_DIRECTORY,
        exist_ok=True,
    )

    file_handler = logging.FileHandler(
        LOG_FILE,
        mode="a",
        encoding="utf-8",
    )

    file_handler.setLevel(logging.INFO)

    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    root_logger.addHandler(file_handler)


def get_logger(name):
    """Retourne un logger configuré pour un module."""
    configure_logging()

    return logging.getLogger(name)


class Timer:
    """Mesure le temps d'exécution d'un bloc de code."""

    def __enter__(self):
        """Démarre le chronomètre."""
        self.start = time.perf_counter()
        self.elapsed = 0.0

        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        """Arrête le chronomètre."""
        self.elapsed = time.perf_counter() - self.start
