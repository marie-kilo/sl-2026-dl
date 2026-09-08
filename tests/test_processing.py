"""Tests de la transformation Raw vers Curated."""

import duckdb

EXPECTED_CURATED_COUNT = 2


def test_cleaning_rules(tmp_path):
    """Vérifie que les règles de nettoyage conservent les lignes valides."""
    raw_file = tmp_path / "raw.parquet"
    curated_file = tmp_path / "curated.parquet"

    connection = duckdb.connect()

    try:
        connection.execute(
            """
            CREATE TABLE source AS
            SELECT *
            FROM (
                VALUES
                    ('R1', 'T1', 'S1', 'Station A', 48.85, 2.35),
                    ('R1', 'T1', 'S2', 'Station B', 48.86, 2.36),
                    (NULL, 'T1', 'S3', 'Station C', 48.87, 2.37)
            ) AS t(
                route_id,
                route_short_name,
                stop_id,
                stop_name,
                stop_lat,
                stop_lon
            )
            """
        )

        connection.execute(
            f"""
            COPY source
            TO '{raw_file}'
            (FORMAT PARQUET)
            """
        )

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
                FROM read_parquet('{raw_file}')
                WHERE route_id IS NOT NULL
                  AND stop_id IS NOT NULL
                  AND stop_name IS NOT NULL
                  AND stop_lat BETWEEN -90 AND 90
                  AND stop_lon BETWEEN -180 AND 180
            )
            TO '{curated_file}'
            (FORMAT PARQUET)
            """
        )

        count = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM read_parquet('{curated_file}')
            """
        ).fetchone()[0]

        assert count == EXPECTED_CURATED_COUNT

    finally:
        connection.close()
