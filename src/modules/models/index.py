
from sentence_transformers import SentenceTransformer

# Load embedding model once when the server starts
model = SentenceTransformer("all-MiniLM-L6-v2")

def embed_text(req):
    embedding = model.encode(req).tolist()
    return embedding

