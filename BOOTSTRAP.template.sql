-- BOOTSTRAP.template.sql
--
-- Run ONCE at the end of intake, before Phase 1. Creates the demo-specific
-- role, the demo database, and grants the role exactly the privileges it
-- needs and no more. Every subsequent operation in the demo runs as
-- RAI_DEMO_<DOMAIN>, which Snowflake itself blocks from touching anything
-- outside the demo database.
--
-- Substitutions to make before running (agent does this at intake):
--   {{DEMO_DB}}       the demo database name (e.g. PK_SUPPLY_CHAIN)
--   {{DEMO_ROLE}}     the demo role name (e.g. RAI_DEMO_SUPPLY_CHAIN)
--   {{DEMO_WAREHOUSE}} the demo warehouse name (default: RAI_XS)
--   {{CURRENT_USER}}  the username the role is granted to
--   {{RAI_APP_NAME}}  the RelationalAI Native App name on this account
--                    (find it: SHOW APPLICATIONS LIKE '%RAI%';)
--
-- This file is the one place the agent runs as ACCOUNTADMIN. From here on,
-- every snow sql call passes --role {{DEMO_ROLE}} explicitly. The user
-- reviews this file before it runs; that is the security gate.

USE ROLE ACCOUNTADMIN;

-- 1. Demo-specific role
CREATE ROLE IF NOT EXISTS {{DEMO_ROLE}}
  COMMENT = 'Scoped role for the {{DEMO_DB}} demo. Created by demo-agent-template intake.';
GRANT ROLE {{DEMO_ROLE}} TO USER {{CURRENT_USER}};
GRANT ROLE {{DEMO_ROLE}} TO ROLE SYSADMIN;

-- 2. Demo database, fully owned by the demo role
CREATE DATABASE IF NOT EXISTS {{DEMO_DB}}
  COMMENT = 'Demo database for {{DEMO_DB}}. Created by demo-agent-template intake.';
GRANT OWNERSHIP ON DATABASE {{DEMO_DB}} TO ROLE {{DEMO_ROLE}} COPY CURRENT GRANTS;
GRANT ALL ON DATABASE {{DEMO_DB}} TO ROLE {{DEMO_ROLE}};
GRANT ALL ON ALL SCHEMAS IN DATABASE {{DEMO_DB}} TO ROLE {{DEMO_ROLE}};
GRANT ALL ON FUTURE SCHEMAS IN DATABASE {{DEMO_DB}} TO ROLE {{DEMO_ROLE}};
GRANT ALL ON ALL TABLES IN DATABASE {{DEMO_DB}} TO ROLE {{DEMO_ROLE}};
GRANT ALL ON FUTURE TABLES IN DATABASE {{DEMO_DB}} TO ROLE {{DEMO_ROLE}};
GRANT ALL ON ALL VIEWS IN DATABASE {{DEMO_DB}} TO ROLE {{DEMO_ROLE}};
GRANT ALL ON FUTURE VIEWS IN DATABASE {{DEMO_DB}} TO ROLE {{DEMO_ROLE}};
GRANT ALL ON ALL STAGES IN DATABASE {{DEMO_DB}} TO ROLE {{DEMO_ROLE}};
GRANT ALL ON FUTURE STAGES IN DATABASE {{DEMO_DB}} TO ROLE {{DEMO_ROLE}};
GRANT ALL ON ALL FUNCTIONS IN DATABASE {{DEMO_DB}} TO ROLE {{DEMO_ROLE}};
GRANT ALL ON FUTURE FUNCTIONS IN DATABASE {{DEMO_DB}} TO ROLE {{DEMO_ROLE}};
GRANT ALL ON ALL PROCEDURES IN DATABASE {{DEMO_DB}} TO ROLE {{DEMO_ROLE}};
GRANT ALL ON FUTURE PROCEDURES IN DATABASE {{DEMO_DB}} TO ROLE {{DEMO_ROLE}};
GRANT ALL ON ALL FILE FORMATS IN DATABASE {{DEMO_DB}} TO ROLE {{DEMO_ROLE}};
GRANT ALL ON FUTURE FILE FORMATS IN DATABASE {{DEMO_DB}} TO ROLE {{DEMO_ROLE}};
GRANT ALL ON ALL NOTEBOOKS IN DATABASE {{DEMO_DB}} TO ROLE {{DEMO_ROLE}};
GRANT ALL ON FUTURE NOTEBOOKS IN DATABASE {{DEMO_DB}} TO ROLE {{DEMO_ROLE}};

-- 3. Warehouse usage (no mutations - the role cannot ALTER or DROP it)
GRANT USAGE ON WAREHOUSE {{DEMO_WAREHOUSE}} TO ROLE {{DEMO_ROLE}};
GRANT OPERATE ON WAREHOUSE {{DEMO_WAREHOUSE}} TO ROLE {{DEMO_ROLE}};

-- 4. RelationalAI Native App access
-- Verify the app name first by running: SHOW APPLICATIONS LIKE '%RAI%';
-- and then: SHOW APPLICATION ROLES IN APPLICATION {{RAI_APP_NAME}};
-- The role we need is typically RAI_DEVELOPER or similar.
GRANT APPLICATION ROLE {{RAI_APP_NAME}}.RAI_DEVELOPER TO ROLE {{DEMO_ROLE}};
GRANT APPLICATION ROLE {{RAI_APP_NAME}}.RAI_USER TO ROLE {{DEMO_ROLE}};

-- 5. Snowflake Intelligence (Cortex agent deployment)
-- The agent is deployed under SNOWFLAKE_INTELLIGENCE.AGENTS. Grant the
-- minimum needed to register and update one agent.
GRANT USAGE ON DATABASE SNOWFLAKE_INTELLIGENCE TO ROLE {{DEMO_ROLE}};
GRANT USAGE ON SCHEMA SNOWFLAKE_INTELLIGENCE.AGENTS TO ROLE {{DEMO_ROLE}};
GRANT CREATE AGENT ON SCHEMA SNOWFLAKE_INTELLIGENCE.AGENTS TO ROLE {{DEMO_ROLE}};

-- 6. Verify the role can do what it needs
USE ROLE {{DEMO_ROLE}};
USE DATABASE {{DEMO_DB}};
USE WAREHOUSE {{DEMO_WAREHOUSE}};
SELECT CURRENT_ROLE() AS role, CURRENT_DATABASE() AS db, CURRENT_WAREHOUSE() AS wh;

-- 7. Document what the role explicitly does NOT have
-- (no DDL outside {{DEMO_DB}}, no USER mutations, no PAT creation, no
-- account-level grants, no warehouse creation, no role mutations).
-- Snowflake denies these by default for any non-ACCOUNTADMIN/SECURITYADMIN
-- role - this script never grants them.

-- End of bootstrap. From this point on, every snow sql command runs as:
--   snow sql --role {{DEMO_ROLE}} -c rai -q '...'
-- See CLAUDE.md > "Snowflake security harness" for the full rule.
