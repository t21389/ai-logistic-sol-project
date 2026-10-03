import os
import urllib.parse
import requests

from pathlib import Path
from dotenv import load_dotenv

from langchain_core.tools import tool
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

from sqlalchemy import create_engine, text



# Environment Set
project_root = Path(__file__).resolve().parent.parent
print("project_root ",project_root)

load_dotenv(dotenv_path=project_root / ".env")

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
EMBEDDING_MODEL_SETTINGS = os.getenv("Embeddings_model")

if not PINECONE_API_KEY:
    raise ValueError("CRITICAL : Pinecone APpi not found")

if EMBEDDING_MODEL_SETTINGS == "OPENAI":
    print("🤖 Mode: Connecting to Cloud OpenAI Index (1536 Dim Space)...")
    embeddings = OpenAIEmbeddings()
    INDEX_NAME = "fde-sop-index-openai"

#  get store and retrieve top 2 search results
vector_store = PineconeVectorStore(index_name=INDEX_NAME, embedding=embeddings)
retriever = vector_store.as_retriever(search_kwargs={"k": 2})

#  Core agent tools
db_host = os.getenv("SQL_SERVER_HOST", "localhost")
db_port = os.getenv("SQL_SERVER_PORT", "5432")
db_user = os.getenv("SQL_AGENT_USER", "USR_FDE_RO")
db_password = os.getenv("SQL_AGENT_PASSWORD")

@tool
def query_telemetry_db(sql_query: str) -> str:
    """
    Executes a SQL SELECT query against the fde_views.vw_active_fleet view.
    Columns available (case-sensitive, use double quotes if needed):
    "Timestamp", "Latitude", "Longitude", "Current_Temperature_C", "Cargo_Condition_Code",
    "Risk_Classification", "Delay_Probability", "Port_Congestion_Level", "Route_Risk_Index".
    Always write standard PostgreSQL queries.
    """
    # URL-encode credentials to safely handle special characters in passwords
    encoded_user = urllib.parse.quote_plus(db_user)
    encoded_password = urllib.parse.quote_plus(db_password)
    
    # Construct PostgreSQL SQLAlchemy connection string
    connection_url = f"postgresql+psycopg2://{encoded_user}:{encoded_password}@{db_host}:{db_port}/master"
    
    engine = create_engine(connection_url)
    
    try:
        # Sanity check: Enforce read-only SELECT queries
        if not sql_query.strip().upper().startswith("SELECT"):
            return "SECURITY BLOCK: Only SELECT operations are authorized on this view."
            
        with engine.connect() as conn:
            cursor = conn.execute(text(sql_query))
            columns = list(cursor.keys())
            rows = cursor.fetchmany(10)
            
            if not rows:
                return "No records matched the query criteria."
                
            formatted_output = f"COLUMNS: {', '.join(columns)}\n"
            for row in rows:
                formatted_output += str(tuple(row)) + "\n"
                
            return formatted_output
            
    except Exception as e:
        return f"Database Error: {str(e)}"



@tool
def fetch_corridor_conditions(latitude: float, longitude: float) -> str:
    """
    Fetches real-time weather and corridor conditions from a live REST API for given GPS coordinates.
    Provides temperature, wind speed, and computed corridor congestion index.
    """
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"
        response = requests.get(url, timeout=6)
        response.raise_for_status()

        payload = response.json().get("current_weather", {})
        temp = payload.get("temperature", "N/A")
        wind = payload.get("windspeed", 0.0)

        congestion_index = 8.5 if wind > 10.0 else 2.5
        status_note = "High Transit Disruption" if wind > 10.0 else "Corridor Normal"
         
        return (
            f"--- LIVE CORRIDOR TELEMETRY ---\n"
            f"Target GPS: {latitude}, {longitude}\n"
            f"External Temp: {temp}°C | Wind Speed: {wind} km/h\n"
            f"Corridor Risk: {status_note} (Congestion Index: {congestion_index}/10)\n"
            f"-------------------------------"
        )
    except Exception as e:
        return f"Corridor API Communication Failure: {str(e)}"
        


@tool
def search_compliance_sop(query: str) -> str:
    """
    Searches enterprise Standard Operating Procedures (SOPs) indexed in the Pinecone Vector DB.
    Use this to retrieve regulatory thresholds, cold-chain breach mitigations, and rerouting rules.
    """
    try:
        matched_docs = retriever.invoke(query)
        if not matched_docs:
            return "No matching compliance clauses found."
            
        formatted_context = "\n\n".join(
            [f"[Source: {doc.metadata.get('source_file', 'SOP')} | Format: {doc.metadata.get('file_format', 'RAW')}]\n{doc.page_content}" for doc in matched_docs]
        )
        return f"--- COMPLIANCE SOP CONTEXT ---\n{formatted_context}\n------------------------------"
    except Exception as e:
        return f"Vector Store Retrieval Error: {str(e)}"



# Local Verificaiton
if __name__ == "__main__":
    print("\n--- Testing Tool 1: SQL Telemetry View ---")
    print(query_telemetry_db.invoke("""SELECT "Latitude", "Longitude", "Current_Temperature_C" 
    FROM fde_views.vw_active_fleet LIMIT 2;"""))
    
    print("\n--- Testing Tool 2: Live Corridor API ---")
    print(fetch_corridor_conditions.invoke({"latitude": 28.6139, "longitude": 77.2090}))
    
    print("\n--- Testing Tool 3: Pinecone Vector Retrieval ---")
    print(search_compliance_sop.invoke("What are the temperature rules for fresh perishables?"))
