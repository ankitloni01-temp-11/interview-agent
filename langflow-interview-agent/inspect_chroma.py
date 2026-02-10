import os
import sys
from dotenv import load_dotenv

# Load env for API key
load_dotenv()

# Add current dir to path
sys.path.append(os.getcwd())

try:
    from src.vector_store import SchemaVectorStore
    
    print("Initializing Vector Store viewer...")
    vs = SchemaVectorStore("data/chroma_db")
    
    count = vs.collection.count()
    print(f"\nTotal Documents in Collection: {count}")
    
    # Get all items
    data = vs.collection.get()
    
    ids = data['ids']
    metas = data['metadatas']
    docs = data['documents']
    
    print("\n" + "="*80)
    print(" EXISTING CHUNKS ")
    print("="*80 + "\n")
    
    for i, doc_id in enumerate(ids):
        print(f"ID: {doc_id}")
        print(f"Type: {metas[i].get('type', 'unknown')}")
        print(f"Table: {metas[i].get('table', 'unknown')}")
        if 'name' in metas[i]:
            print(f"Name: {metas[i]['name']}")
            
        print("-" * 40)
        print(f"Media/Content:\n{docs[i].strip()}")
        print("\n" + "="*80 + "\n")

except Exception as e:
    print(f"Error inspecting DB: {e}")
