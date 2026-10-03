# input the file 
# should support all format like .md, .txt, .csv, .pdf, .xlsx
# different splitiing technique for the various format 
# connection to the vector db 
# store it : chunks > embedding > pinecone index

import os
import json
import hashlib

from dotenv import load_dotenv
from pathlib import Path
from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter


# path resolution
script_dir = Path(__file__).parent
project_root = script_dir.parent
load_dotenv(project_root / ".env")

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not PINECONE_API_KEY:
    raise ValueError("<missing pinecone api key in .env")

# Dynamic embedding env setting 
EMBEDDING_MODEL_SETTING = os.getenv("Embeddings_model", "LOCAL").strip()

if EMBEDDING_MODEL_SETTING == "OPENAI":
    print("🤖 Mode: Utilizing Cloud OpenAI Embeddings ...")
    embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)
    INDEX_NAME = "fde-sop-index-openai"  # Isolated OpenAI Index
    TARGET_DIMENSION = 1536
else:
     local_model_target = os.getenv("Local_Embedding_Model", "BAAI/bge-m3").strip()
     print(f"🤗 Mode: Local Fallback Settings Activated. Launching [{local_model_target}] (1024 Dim)...")
     from langchain_huggingface import HuggingFaceEmbeddings
     embeddings = HuggingFaceEmbeddings(
        model_name=local_model_target,   # Passes parameter dynamically
        model_kwargs={'device': 'cpu'}
     )
     INDEX_NAME = "fde-sop-index-local"   # Isolated Local Model Index
     TARGET_DIMENSION = 1024              # Standard width for BGE-M3

# Pinecone Provisioning 
print(f"Connecting to Pinecone Index Target: [{INDEX_NAME}]...")
pc = Pinecone(
    api_key=PINECONE_API_KEY
)

existing_indexes = pc.list_indexes().names()

print("existing indexes", existing_indexes)

# verification in case of an existing index
if INDEX_NAME in existing_indexes:
    dec = pc.describe_index(INDEX_NAME)
    print("Index_Name ", INDEX_NAME, dec)
    if dec.dimension != TARGET_DIMENSION:
        print(f"Fixing tracking: Purging mismatched {dec.dimension}")
        pc.delete_index(INDEX_NAME)
        existing_indexes = [name for name in existing_indexes if name != INDEX_NAME]

if INDEX_NAME not in existing_indexes:
    print(f"Creating isloated target Index: {INDEX_NAME} {TARGET_DIMENSION}")
    pc.create_index(
        name=INDEX_NAME,
        dimension=TARGET_DIMENSION, 
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )

index_client = pc.Index(INDEX_NAME)
vector_store = PineconeVectorStore(index_name=INDEX_NAME, embedding=embeddings) 
print("Created Index_Client and Store: ", index_client, vector_store)
# Test store 
# vector_store.add_texts("My name is Pinecone")



# Read from Policy : Create Pipeline
policy_dir = project_root / "data" / "policy"
target_patterns = ["*.md", "*.txt", "*.pdf", "*.csv", "*.xlsx"]
current_files = {}

for pattern in target_patterns:
    for file_path in policy_dir.glob(pattern):
        current_files[file_path.name] = file_path

print(f"Found files : {len(current_files)} policy files in {policy_dir}")

def parse_and_chunk_document(doc_path: Path) -> list[Document]:
    ext = doc_path.suffix.lower()
    print(f"Extension of file {doc_path} -> {ext}")    
    raw_chunks: list[Document] = []
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=60)

    if ext == ".md":
        headers_to_split_on = [("#", "Header_1"), ("##", "Header_2"), ("###", "Header_3")]
        md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        raw_text = doc_path.read_text(encoding="utf-8")
        header_docs = md_splitter.split_text(raw_text)
        raw_chunks = text_splitter.split_documents(header_docs)

    # sanity checks on chunk
    valid_chunks = []
    for chunk in raw_chunks:
        clean_text = chunk.page_content.strip()
        if clean_text:
            chunk.page_content = clean_text
            valid_chunks.append(chunk)

    return valid_chunks

# Cache check 
updated_cache  = {}
cache_modified = False
cache_dir = project_root / "data" / "cache"
cache_dir.mkdir(parents=True, exist_ok=True)
HASH_CACHE_FILE = cache_dir / "ingestion_hash_cache.json"
hash_cache = {}
print("HASH_CACHE_FILE.exists() ", HASH_CACHE_FILE.exists())

if HASH_CACHE_FILE.exists():
    try:
        with open(HASH_CACHE_FILE, "r") as f:
            hash_cache = json.load(f)
    except Exception:
        hash_cache = {}


        
        

# Reading File and insert chuks 
for file_name, file_path in current_files.items():
    # hash calculation and change detection
    file_bytes = file_path.read_bytes()
    file_hash = hashlib.md5(file_bytes).hexdigest()
    # update cachec with the hash
    updated_cache[file_name] = file_hash

    # will save the computation and tokens as hash matching no need to go furhter
    if hash_cache.get(file_name) == file_hash:
        print(f"✨ Skipped (Unchanged): {file_name}")
        continue

    print(f"🔄 Processing updates: {file_name}...")
    cache_modified = True
    
    try: 
        chunks = parse_and_chunk_document(file_path)        
        if not chunks:
            print(f"  ❌ No valid chunks found for {file_name}. Skipping ingestion.")
            continue

        explicit_ids = []

        for idx, chunk in enumerate(chunks):
            chunk.metadata["source_file"] = file_name
            chunk.metadata["file_format"] = file_path.suffix.replace(".", "").upper()
            chunk.metadata["document_type"] = "Compliance Asset"
            explicit_ids.append(f"{file_name}-chunk-{idx}")
            batch_size = 100
            total_chunks = len(chunks)
            print(f"  📤 Upserting {total_chunks} chunk(s) in batches of {batch_size}...")

        for i in range(0, total_chunks, batch_size):
            batch_docs = chunks[i : i + batch_size]
            batch_ids = explicit_ids[i : i + batch_size]
            print(f"Batch docs and ids {batch_docs} {batch_ids}")
            vector_store.add_documents(documents=batch_docs, ids=batch_ids)

    except Exception as e:
        print(f"Error during ingestion of {file_name} : {e}")
        updated_cache.pop(file_name, None)


# ==========================================
# 6. SYNC HASH CACHE
# ==========================================
if cache_modified:
    with open(HASH_CACHE_FILE, "w") as f:
        json.dump(updated_cache, f, indent=4)
    print("✅ Ingestion & cache update complete.")
else:
    print("🌴 Index is already up-to-date.")

