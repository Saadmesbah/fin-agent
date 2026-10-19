from sentence_transformers import SentenceTransformer

model = SentenceTransformer("BAAI/bge-small-en-v1.5")
vec = model.encode("Apple relies on outsourcing partners in Asia.")
print(vec.shape)