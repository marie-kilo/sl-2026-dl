"""Tests de la construction des documents MongoDB."""

from collections import defaultdict

EXPECTED_DOCUMENT_COUNT = 1
EXPECTED_STOP_COUNT = 2


def build_documents(rows):
    """Construit des documents MongoDB à partir de lignes de test."""
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

    for route_id, route_data in routes.items():
        documents.append(
            {
                "route_id": route_id,
                "route_short_name": route_data["route_short_name"],
                "stops": route_data["stops"],
            }
        )

    return documents


def test_build_documents():
    """Vérifie qu'une route contient bien ses arrêts imbriqués."""
    rows = [
        (
            "R1",
            "T1",
            "S1",
            "Station A",
            48.85,
            2.35,
        ),
        (
            "R1",
            "T1",
            "S2",
            "Station B",
            48.86,
            2.36,
        ),
    ]

    documents = build_documents(rows)

    assert len(documents) == EXPECTED_DOCUMENT_COUNT
    assert documents[0]["route_id"] == "R1"
    assert documents[0]["route_short_name"] == "T1"
    assert len(documents[0]["stops"]) == EXPECTED_STOP_COUNT
    assert documents[0]["stops"][0]["stop_id"] == "S1"
