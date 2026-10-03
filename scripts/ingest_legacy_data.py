from pathlib import Path
import pandas as pd
import urllib.parse
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

# __file__ is 'experiment/phase-0/ingest_legacy_data.py'
script_dir = Path(__file__).resolve().parent   # points to 'scripts'
project_root = script_dir.parent               # climbs up 1 level to 'ai-logistic-sol-project'

load_dotenv(project_root / ".env")

data_path = project_root / "data" / "raw" / "dynamic_supply_chain_logistics_dataset.csv"

db_host = os.getenv("SQL_SERVER_HOST", "localhost")
db_user = os.getenv("SQL_ADMIN_USER", "postgres")
db_password = os.getenv("SQL_ADMIN_PASSWORD")

# 1. Load the raw dataset
print(f"Loading CSV from {data_path}...")
df = pd.read_csv(data_path)

# 2. Map clean columns to a messy 2000s legacy enterprise schema
legacy_mapping = {
    'timestamp': 'TS_UTC',
    'vehicle_gps_latitude': 'V_LAT',
    'vehicle_gps_longitude': 'V_LON',
    'iot_temperature': 'IOT_TEMP_VAL_C',
    'cargo_condition_status': 'CGO_COND_CD',
    'risk_classification': 'RISK_CLS_TXT',
    'delay_probability': 'DELAY_PROB_DEC',
    'port_congestion_level': 'PRT_CNG_LVL',
    'route_risk_level': 'RT_RSK_IDX'
}

# Keep only the columns we mapped for this demo and rename them
df_legacy = df[list(legacy_mapping.keys())].rename(columns=legacy_mapping)

# Add a fake ingestion flag to make it look like an automated legacy system
df_legacy['SYS_INGEST_FLAG'] = 'Y'

# 3. Connect to Docker PostgreSQL Server
print("Connecting to legacy PostgreSQL Database...")

# URL-encoding the password in case it contains special characters
safe_user = urllib.parse.quote_plus(db_user) if db_user else "postgres"
safe_password = urllib.parse.quote_plus(db_password) if db_password else ""

# PostgreSQL standard port is 5432
connection_url = f"postgresql+psycopg2://{safe_user}:{safe_password}@{db_host}:5432/master"

engine = create_engine(connection_url)

# 4. Ingest data into the messy table name
table_name = 'tbl_sc_fleet_hist_raw'
print(f"Ingesting into {table_name}. This may take a minute...")
df_legacy.to_sql(table_name, engine, if_exists='replace', index=False, schema='public')

print("✅ Legacy data ingestion complete!")
