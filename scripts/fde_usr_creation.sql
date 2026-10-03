-- 1. Create the Read-Only Role/User if it doesn't already exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'usr_fde_ro') THEN
        CREATE ROLE usr_fde_ro WITH LOGIN PASSWORD 'AgentPassword2026!';
    END IF;
END $$;

-- 2. Revoke default access to public tables to prevent accidental leaks
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM usr_fde_ro;
REVOKE ALL ON SCHEMA public FROM usr_fde_ro;

-- 3. Grant USAGE access ONLY to fde_views schema
GRANT USAGE ON SCHEMA fde_views TO usr_fde_ro;

-- 4. Grant SELECT access ONLY to the semantic view
GRANT SELECT ON fde_views.vw_active_fleet TO usr_fde_ro;