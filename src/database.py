"""
Everything related to the local vector database lives here.
We use ChromaDB with its default sentence-transformer embeddings,
so no extra embedding API calls are needed.
"""

import json
import os
import chromadb
from chromadb.utils import embedding_functions

from src.config import chroma_db_path, collection_name


def get_client():
    """Returns a ChromaDB client that persists data to ./chroma_db."""
    return chromadb.PersistentClient(path=chroma_db_path)


def get_collection(client):
    """Fetches (or creates) the collection we store sports facts in."""
    embedder = embedding_functions.DefaultEmbeddingFunction()
    return client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedder,
    )


def seed_database(facts_path="./data/sports_facts.json"):
    """
    Loads facts from the JSON file and inserts them into ChromaDB.
    Skips re-inserting if the collection is already populated, so
    this is safe to call every time the app starts.
    """
    client = get_client()
    collection = get_collection(client)

    if collection.count() > 0:
        print(f"Vector DB already has {collection.count()} facts loaded.")
        return collection

    if not os.path.exists(facts_path):
        print(f"Could not find facts file at {facts_path}")
        return collection

    with open(facts_path, "r") as f:
        raw_facts = json.load(f)

    fact_texts = []
    fact_metadata = []
    fact_ids = []

    for i, entry in enumerate(raw_facts):
        fact_texts.append(entry["fact"])
        fact_metadata.append({"sport": entry["sport"]})
        fact_ids.append(f"fact_{i}")

    collection.add(documents=fact_texts, metadatas=fact_metadata, ids=fact_ids)
    print(f"Loaded {len(fact_texts)} facts into the vector database.")
    return collection


def find_relevant_facts(sport, search_text, max_results=3):
    """
    Returns the most relevant stored facts for a given sport.
    Falls back to an empty list if nothing matches.
    """
    client = get_client()
    collection = get_collection(client)

    results = collection.query(
        query_texts=[search_text],
        n_results=max_results,
        where={"sport": sport},
    )

    matched_docs = results.get("documents", [[]])[0]
    return matched_docs
