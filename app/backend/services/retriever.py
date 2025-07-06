# %% Import modules
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from langchain_huggingface import HuggingFaceEmbeddings
from app.backend.db.qdrant_db import QdrantDB
from app.backend.services.user_manager import UserIdentifier

# %%
# Initialize the embedding model.
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Define the collection name (based on the user)
username = "AverageJoe"
collection_name = UserIdentifier.get_collection_name(username)

# Create an instance of QdrantDB.
db = QdrantDB(collection_name=collection_name, embedding_model=embedding_model)

# Execute a similarity search example.
query = "what do they say about the future of tech careers in relation to AI?"
results = db.search(query, k=5)

for i, doc in enumerate(results):
    print(f"\nCHUNK {i+1}:\n{doc.page_content}")