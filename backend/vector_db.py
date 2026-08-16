import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# Initialize ChromaDB client in a local directory
chroma_client = chromadb.PersistentClient(path="./chroma_db", settings=Settings(allow_reset=True))

# Get or create a collection for our evidence
collection = chroma_client.get_or_create_collection(
    name="evidence_collection",
    metadata={"hnsw:space": "cosine"}
)

# Initialize the embedding model locally
# all-MiniLM-L6-v2 is a good free local sentence transformers model
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

def add_evidence_to_vector_store(evidence_id: int, text: str, metadata: dict):
    """
    Embeds the text and adds it to the ChromaDB collection.
    """
    embedding = embedding_model.encode(text).tolist()
    
    collection.add(
        ids=[str(evidence_id)],
        embeddings=[embedding],
        documents=[text],
        metadatas=[metadata]
    )

def search_evidence(query: str, n_results: int = 5):
    """
    Searches the vector store for the query and returns the top results.
    """
    query_embedding = embedding_model.encode(query).tolist()
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )
    return results
