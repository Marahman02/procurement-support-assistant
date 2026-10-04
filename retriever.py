"""Index past support tickets in ChromaDB and search them by similarity."""

import json
from pathlib import Path

import chromadb

BASE_DIR = Path(__file__).resolve().parent
TICKETS_PATH = BASE_DIR / "data" / "tickets.json"
DB_PATH = BASE_DIR / "chroma_db"
COLLECTION_NAME = "tickets"


def _client():
    return chromadb.PersistentClient(path=str(DB_PATH))


def _ticket_text(ticket):
    return (
        f"Symptom: {ticket['symptom']}\n"
        f"Root cause: {ticket['root_cause']}\n"
        f"Resolution: {ticket['resolution']}\n"
        f"Category: {ticket['category']}"
    )


def build_index():
    """Load tickets from data/tickets.json and (re)build the Chroma collection."""
    tickets = json.loads(TICKETS_PATH.read_text(encoding="utf-8"))
    client = _client()

    # Start from an empty collection so removed or edited tickets don't linger.
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass  # Collection doesn't exist yet.
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    collection.add(
        ids=[t["id"] for t in tickets],
        documents=[_ticket_text(t) for t in tickets],
        metadatas=[{"category": t["category"]} for t in tickets],
    )
    return len(tickets)


def search(query, k=3):
    """Return the k most similar tickets as dicts with id, similarity and text."""
    collection = _client().get_collection(COLLECTION_NAME)
    results = collection.query(query_texts=[query], n_results=k)

    return [
        {"id": ticket_id, "similarity": 1 - distance, "text": text}
        for ticket_id, distance, text in zip(
            results["ids"][0], results["distances"][0], results["documents"][0]
        )
    ]


if __name__ == "__main__":
    print(f"Indexed {build_index()} tickets.")
    for match in search("invoice blocked because the price is higher than the PO"):
        print(f"{match['id']}  {match['similarity']:.3f}")
