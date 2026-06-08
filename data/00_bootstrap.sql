-- 00_bootstrap.sql
--
-- One-shot bootstrap for the Nestle diet/menu-optimization RelationalAI demo.
-- Creates a demo-specific role, the demo database, and grants the role exactly
-- the privileges it needs and no more. After this runs, every subsequent
-- snow sql command in this repo passes --role RAI_DEMO_NESTLE_DIET explicitly.
-- Snowflake itself blocks the demo role from touching anything outside
-- PK_NESTLE_DIET.
--
-- Substitutions already applied (verified against the working bmw_demo bootstrap
-- on this account):
--   DEMO_DB        = PK_NESTLE_DIET
--   DEMO_ROLE      = RAI_DEMO_NESTLE_DIET
--   DEMO_WAREHOUSE = RAI_XS
--   CURRENT_USER   = "piotr.kraus@relational.ai"
--   RAI_APP_NAME   = RELATIONALAI
--
-- Account: ajb85638 (Snowflake SE US). The user reviews this file and runs it
-- ONCE via:   snow sql -c rai -f data/00_bootstrap.sql
-- (Requires a valid rai connection; refresh the programmatic access token first
-- if snow reports it expired.)
--
-- See CLAUDE.md > "Snowflake security harness" for the full model.

USE ROLE ACCOUNTADMIN;

-- 1. Demo-specific role
CREATE ROLE IF NOT EXISTS RAI_DEMO_NESTLE_DIET
  COMMENT = 'Scoped role for the PK_NESTLE_DIET demo (vegan diet/menu optimization). Created by demo-agent-template intake.';
GRANT ROLE RAI_DEMO_NESTLE_DIET TO USER "piotr.kraus@relational.ai";
GRANT ROLE RAI_DEMO_NESTLE_DIET TO ROLE SYSADMIN;

-- 2. Demo database, fully owned by the demo role
CREATE DATABASE IF NOT EXISTS PK_NESTLE_DIET
  COMMENT = 'Demo database for the Nestle vegan diet/menu optimization demo. Created by demo-agent-template intake.';
GRANT OWNERSHIP ON DATABASE PK_NESTLE_DIET TO ROLE RAI_DEMO_NESTLE_DIET COPY CURRENT GRANTS;
GRANT ALL ON DATABASE PK_NESTLE_DIET TO ROLE RAI_DEMO_NESTLE_DIET;
GRANT ALL ON ALL SCHEMAS IN DATABASE PK_NESTLE_DIET TO ROLE RAI_DEMO_NESTLE_DIET;
GRANT ALL ON FUTURE SCHEMAS IN DATABASE PK_NESTLE_DIET TO ROLE RAI_DEMO_NESTLE_DIET;
GRANT ALL ON ALL TABLES IN DATABASE PK_NESTLE_DIET TO ROLE RAI_DEMO_NESTLE_DIET;
GRANT ALL ON FUTURE TABLES IN DATABASE PK_NESTLE_DIET TO ROLE RAI_DEMO_NESTLE_DIET;
GRANT ALL ON ALL VIEWS IN DATABASE PK_NESTLE_DIET TO ROLE RAI_DEMO_NESTLE_DIET;
GRANT ALL ON FUTURE VIEWS IN DATABASE PK_NESTLE_DIET TO ROLE RAI_DEMO_NESTLE_DIET;
GRANT ALL ON ALL STAGES IN DATABASE PK_NESTLE_DIET TO ROLE RAI_DEMO_NESTLE_DIET;
GRANT ALL ON FUTURE STAGES IN DATABASE PK_NESTLE_DIET TO ROLE RAI_DEMO_NESTLE_DIET;
GRANT ALL ON ALL FUNCTIONS IN DATABASE PK_NESTLE_DIET TO ROLE RAI_DEMO_NESTLE_DIET;
GRANT ALL ON FUTURE FUNCTIONS IN DATABASE PK_NESTLE_DIET TO ROLE RAI_DEMO_NESTLE_DIET;
GRANT ALL ON ALL PROCEDURES IN DATABASE PK_NESTLE_DIET TO ROLE RAI_DEMO_NESTLE_DIET;
GRANT ALL ON FUTURE PROCEDURES IN DATABASE PK_NESTLE_DIET TO ROLE RAI_DEMO_NESTLE_DIET;
GRANT ALL ON ALL FILE FORMATS IN DATABASE PK_NESTLE_DIET TO ROLE RAI_DEMO_NESTLE_DIET;
GRANT ALL ON FUTURE FILE FORMATS IN DATABASE PK_NESTLE_DIET TO ROLE RAI_DEMO_NESTLE_DIET;
-- NOTEBOOK is a Snowflake object type that does NOT support GRANT ON ALL /
-- GRANT ON FUTURE (Snowflake error 0A000 "Unsupported feature"). The role
-- already owns the database via the OWNERSHIP grant above, so it can
-- CREATE / ALTER / DROP NOTEBOOKS inside any schema in PK_NESTLE_DIET with no
-- further grant needed.

-- 3. Warehouse usage (USAGE + OPERATE only; no MODIFY so the role cannot
-- ALTER or DROP the warehouse)
GRANT USAGE ON WAREHOUSE RAI_XS TO ROLE RAI_DEMO_NESTLE_DIET;
GRANT OPERATE ON WAREHOUSE RAI_XS TO ROLE RAI_DEMO_NESTLE_DIET;

-- 4. RelationalAI Native App access
-- On ajb85638 the app is named RELATIONALAI. Verified via:
--   SHOW APPLICATIONS LIKE '%RAI%';
--   SHOW APPLICATION ROLES IN APPLICATION RELATIONALAI;
-- The app exposes RAI_USER as an application role; the account-level role
-- RAI_DEVELOPER (installed by the native app) is what PyRel programs rely on.
-- Grant both.
GRANT APPLICATION ROLE RELATIONALAI.RAI_USER TO ROLE RAI_DEMO_NESTLE_DIET;
GRANT ROLE RAI_DEVELOPER TO ROLE RAI_DEMO_NESTLE_DIET;

-- 5. Snowflake Intelligence (Cortex agent deployment)
-- On ajb85638 the SNOWFLAKE_INTELLIGENCE database may not exist. If it does,
-- uncomment to let the demo role register the Cortex agent in the SI picker;
-- otherwise the agent deploys into PK_NESTLE_DIET.RAI_AGENT (owned by the role).
--   GRANT USAGE ON DATABASE SNOWFLAKE_INTELLIGENCE TO ROLE RAI_DEMO_NESTLE_DIET;
--   GRANT USAGE ON SCHEMA SNOWFLAKE_INTELLIGENCE.AGENTS TO ROLE RAI_DEMO_NESTLE_DIET;
--   GRANT CREATE AGENT ON SCHEMA SNOWFLAKE_INTELLIGENCE.AGENTS TO ROLE RAI_DEMO_NESTLE_DIET;

-- 6. Smoke-verify the role
USE ROLE RAI_DEMO_NESTLE_DIET;
USE DATABASE PK_NESTLE_DIET;
USE WAREHOUSE RAI_XS;
SELECT CURRENT_ROLE() AS role, CURRENT_DATABASE() AS db, CURRENT_WAREHOUSE() AS wh;

-- 7. What this role explicitly does NOT have
-- (no DDL outside PK_NESTLE_DIET, no USER mutations, no PAT creation, no
-- account-level grants, no warehouse creation, no role mutations). Snowflake
-- denies these by default for any non-ACCOUNTADMIN / SECURITYADMIN role; this
-- script never grants them.

-- End of bootstrap. From here on, every snow sql command runs as:
--   snow sql --role RAI_DEMO_NESTLE_DIET -c rai -q '...'
--   snow sql --role RAI_DEMO_NESTLE_DIET -c rai -f path/to/file.sql
