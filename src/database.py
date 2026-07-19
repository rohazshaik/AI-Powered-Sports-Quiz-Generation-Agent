import json
import os

import chromadb
from chromadb.utils import embedding_functions

from src.config import chroma_db_path, collection_name


def get_client():
    return chromadb.PersistentClient(path=chroma_db_path)


def get_collection(client):
    embedder = embedding_functions.DefaultEmbeddingFunction()
    return client.get_or_create_collection(name=collection_name, embedding_function=embedder)


def seed_database(facts_path="./data/sports_facts.json"):
    client = get_client()
    collection = get_collection(client)
    existing_count = collection.count()

    if existing_count > 0:
        print(f"Vector DB already has {existing_count} facts loaded.")
        return collection

    if not os.path.exists(facts_path):
        print(f"Could not find facts file at {facts_path}")
        return collection

    with open(facts_path, "r", encoding="utf-8") as file:
        raw_facts = json.load(file)

    texts = []
    metadata = []
    ids = []

    for index, entry in enumerate(raw_facts):
        texts.append(entry["fact"])
        metadata.append({"sport": entry["sport"]})
        ids.append(f"fact_{index}")

    collection.add(documents=texts, metadatas=metadata, ids=ids)
    print(f"Loaded {len(texts)} facts into the vector database.")
    return collection


def find_relevant_facts(sport, search_text, max_results=3):
    client = get_client()
    collection = get_collection(client)

    results = collection.query(query_texts=[search_text], n_results=max_results, where={"sport": sport})

    return results.get("documents", [[]])[0]
