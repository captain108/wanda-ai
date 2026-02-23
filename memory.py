import faiss
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")
index = faiss.IndexFlatL2(384)
texts = []

def add_memory(text):
    vec = model.encode([text])
    index.add(vec)
    texts.append(text)

def search_memory(query, k=3):
    if not texts:
        return []
    qv = model.encode([query])
    D, I = index.search(qv, k)
    return [texts[i] for i in I[0] if i >= 0]
