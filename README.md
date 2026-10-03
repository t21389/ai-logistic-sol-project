# ai-logistic-sol-project

<img width="1274" height="733" alt="Screen Shot 2026-10-03 at 8 49 31 PM" src="https://github.com/user-attachments/assets/642ed81b-c4a6-415c-a7ff-b9f0dcec1398" />
<img width="1263" height="755" alt="Screen Shot 2026-10-03 at 8 49 56 PM" src="https://github.com/user-attachments/assets/e03e3945-4e37-47fd-a561-93fa44c8a2c9" />


Here is the complete, production-grade README.md file for your project in a single copy-paste code block:

Markdown
# 🧊 Cold-Chain Telemetry AI Agent & Dispatch Console

An enterprise-grade, real-time logistics monitoring and decision optimization platform. This system connects an autonomous AI Reasoning Agent (powered by LangGraph) to a secure PostgreSQL telemetry database, providing automated risk assessment, corridor analysis, and interactive incident control via Streamlit.

---

## 🏗️ System Architecture & Workflow

┌─────────────────────────┐      ┌─────────────────────────┐
│                         │      │                         │
│  Streamlit UI Console   │────> │    AI Agent Reasoning   │
│  (Dispatch & Audit)     │      │   Graph (LangChain)     │
│                         │      │                         │
└─────────────────────────┘      └───────────┬─────────────┘
│
▼
┌─────────────────────────┐
│   Tool Layer Execution  │
│  (query_telemetry_db)   │
└───────────┬─────────────┘
│
▼
┌─────────────────────────┐
│ PostgreSQL Database     │
│ Schema: fde_views       │
│ Role:   usr_fde_ro      │
└─────────────────────────┘


---

## 🔒 Security & Semantic Layer Design

To prevent accidental data exposure or destructive SQL operations by the AI agent:
1. **Least Privilege Read-Only Access (`usr_fde_ro`):** The AI agent logs into PostgreSQL using a restricted role with zero direct access to raw underlying database tables.
2. **Semantic View Layer (`fde_views.vw_active_fleet`):** Access is strictly limited to an abstraction view that cleans raw column headers into standardized, case-sensitive attributes (`"Timestamp"`, `"Latitude"`, `"Longitude"`, `"Current_Temperature_C"`, etc.).
3. **Execution Guardrails:** The Python execution tool validates `SELECT` query intent prior to database execution.
4. **Audit Logging:** Every reasoning step, tool call input, and tool output is asynchronously recorded in `fde_views.agent_audit_log`.

---

## 🚀 Getting Started

### 1. Prerequisites
* **Python:** `3.10+`
* **PostgreSQL:** `14+` running on port `5432`

### 2. Environment Setup

Clone the repository and install dependencies:

```bash
git clone [https://github.com/your-org/ai-logistic-sol-project.git](https://github.com/your-org/ai-logistic-sol-project.git)
cd ai-logistic-sol-project

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install streamlit pandas sqlalchemy psycopg2-binary langchain langchain-openai langgraph python-dotenv
3. Required Environment Variables (.env)
Create a .env file in the project root:

Code snippet
# PostgreSQL Agent Credentials (Read-Only)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=master
POSTGRES_USER=usr_fde_ro
POSTGRES_PASSWORD=AgentPassword2026!

# PostgreSQL Admin Credentials (Audit View Access)
POSTGRES_ADMIN_USER=postgres
POSTGRES_ADMIN_PASSWORD=AdminPassword2026!

# LLM Provider Configuration
Agent_llm=DEEPSEEK
DEEPSEEK_API_KEY=your_deepseek_api_key_here
🗄️ Database Initialization DDL (PostgreSQL)
Execute the following script in your target PostgreSQL database as an administrative user (postgres):

SQL
-- 1. Create Schema & Semantic View
CREATE SCHEMA IF NOT EXISTS fde_views;

-- Mock raw table (for reference)
CREATE TABLE IF NOT EXISTS public.tbl_sc_fleet_hist_raw (
    TS_UTC TIMESTAMP,
    V_LAT NUMERIC,
    V_LONG NUMERIC,
    TEMP_C NUMERIC,
    CARGO_CODE VARCHAR(50),
    RISK_CLASS VARCHAR(50),
    DELAY_PROB NUMERIC,
    PORT_CONG VARCHAR(50),
    ROUTE_INDEX NUMERIC
);

CREATE OR REPLACE VIEW fde_views.vw_active_fleet AS
SELECT 
    TS_UTC AS "Timestamp",
    V_LAT AS "Latitude",
    V_LONG AS "Longitude",
    TEMP_C AS "Current_Temperature_C",
    CARGO_CODE AS "Cargo_Condition_Code",
    RISK_CLASS AS "Risk_Classification",
    DELAY_PROB AS "Delay_Probability",
    PORT_CONG AS "Port_Congestion_Level",
    ROUTE_INDEX AS "Route_Risk_Index"
FROM public.tbl_sc_fleet_hist_raw;

-- 2. Create Audit Logging Table
CREATE TABLE IF NOT EXISTS fde_views.agent_audit_log (
    log_id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    session_id VARCHAR(255) NOT NULL,
    node_executed VARCHAR(100) NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    content TEXT
);

-- 3. Create Restricted Read-Only Role & Apply Privileges
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'usr_fde_ro') THEN
        CREATE ROLE usr_fde_ro WITH LOGIN PASSWORD 'AgentPassword2026!';
    END IF;
END
$$;

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM usr_fde_ro;
REVOKE ALL ON SCHEMA public FROM usr_fde_ro;

GRANT USAGE ON SCHEMA fde_views TO usr_fde_ro;
GRANT SELECT ON fde_views.vw_active_fleet TO usr_fde_ro;

-- Audit log write permissions for agent
GRANT SELECT, INSERT ON fde_views.agent_audit_log TO usr_fde_ro;
GRANT USAGE, SELECT ON SEQUENCE fde_views.agent_audit_log_log_id_seq TO usr_fde_ro;
💻 Running the Application
Launch the Streamlit Dispatch Console:

Bash
streamlit run app.py
Navigate to http://localhost:8501 in your browser.

Application Modes:
🧊 Dispatch Console: Interactive agent chat interface featuring streaming updates, tool parameter tracing, and execution payload expanders.

🛡️ Security & Audit Logs: Admin-authenticated interface to inspect user query session traces, reasoning node execution history, and raw outputs stored in fde_views.agent_audit_log.

🛠️ PostgreSQL Agent Query Guidelines
When crafting queries for the telemetry tool:

Row Limiting: Use LIMIT N at the end of the query (do NOT use T-SQL TOP N).

Double Quotes: Identifiers in fde_views.vw_active_fleet are case-sensitive and must be wrapped in double quotes:

SQL
SELECT "Latitude", "Longitude", "Current_Temperature_C" 
FROM fde_views.vw_active_fleet 
LIMIT 5;
