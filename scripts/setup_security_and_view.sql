-- ====================================================================
-- FDE ENTERPRISE SECURITY & SEMANTIC LAYER SCRIPT (PostgreSQL Version)
-- ====================================================================

-- 1. Create a dedicated schema for clean AI views
CREATE SCHEMA IF NOT EXISTS fde_views;

-- 2. Create the Semantic View
CREATE OR REPLACE VIEW fde_views.vw_active_fleet AS
SELECT 
    "TS_UTC" AS "Timestamp",
    "V_LAT" AS "Latitude",
    "V_LON" AS "Longitude",
    CAST("IOT_TEMP_VAL_C" AS DOUBLE PRECISION) AS "Current_Temperature_C",
    "CGO_COND_CD" AS "Cargo_Condition_Code",
    "RISK_CLS_TXT" AS "Risk_Classification",
    "DELAY_PROB_DEC" AS "Delay_Probability",
    "PRT_CNG_LVL" AS "Port_Congestion_Level",
    "RT_RSK_IDX" AS "Route_Risk_Index"
FROM tbl_sc_fleet_hist_raw;

-- 3. Create the Read-Only Role/User
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'usr_fde_ro') THEN
        CREATE ROLE usr_fde_ro WITH LOGIN PASSWORD 'AgentPassword2026!';
    END IF;
END $$;

-- 4. Grant permissions to the view only
GRANT USAGE ON SCHEMA fde_views TO usr_fde_ro;
GRANT SELECT ON fde_views.vw_active_fleet TO usr_fde_ro;