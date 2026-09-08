"""Fournit le client MongoDB utilisé par le projet."""

import os

from pymongo import MongoClient


def get_mongo_client():
    """Crée et retourne un client MongoDB configuré."""
    host = os.getenv("MONGO_HOST", "mongodb")
    port = int(os.getenv("MONGO_PORT", "27017"))
    username = os.getenv("MONGO_USERNAME")
    password = os.getenv("MONGO_PASSWORD")

    return MongoClient(
        host=host,
        port=port,
        username=username,
        password=password,
        authSource="admin",
        serverSelectionTimeoutMS=5000,
    )
