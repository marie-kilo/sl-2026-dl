"""Exemple pédagogique de logging et de chronométrage."""

import time

from src.logger import get_logger
from src.test_funk import my_amazing_funk, other_func

logger = get_logger(__name__)


class Timer:
    """Mesure le temps d'exécution d'un bloc."""

    def __enter__(self):
        """Démarre le chronomètre."""
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        """Arrête le chronomètre."""
        self.elapsed = time.perf_counter() - self.start


def test():
    """Simule une fonction longue."""
    time.sleep(2)


def main_test():
    """Exécute les fonctions de démonstration."""
    logger.info("test func started")

    with Timer() as timer:
        test()

    logger.info(
        "test func ended: %.4f s",
        timer.elapsed,
    )

    logger.info("amazing_funk started")
    my_amazing_funk()
    logger.info("amazing_funk ended")

    other_func()


if __name__ == "__main__":
    main_test()
