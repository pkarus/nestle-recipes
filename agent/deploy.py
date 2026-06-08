"""Deploy the nestle_diet ontology as a Snowflake Intelligence (Cortex) agent.

Run from project root:

    .venv/bin/python -m agent.deploy preflight                    # probe grants
    .venv/bin/python -m agent.deploy setup-sql                    # emit GRANTs
    .venv/bin/python -m agent.deploy deploy                       # create
    .venv/bin/python -m agent.deploy update                       # refresh sprocs
    .venv/bin/python -m agent.deploy status
    .venv/bin/python -m agent.deploy chat "Build Marco's cheapest compliant menu"
    .venv/bin/python -m agent.deploy teardown

The agent is registered at SNOWFLAKE_INTELLIGENCE.AGENTS.nestle_diet so it
appears in Snowsight's Snowflake Intelligence picker. Stored procedures and the
dependency stage live in PK_NESTLE_DIET.RAI_AGENT. If SNOWFLAKE_INTELLIGENCE is
absent / not granted, set AGENT_SCHEMA = None to deploy into
PK_NESTLE_DIET.RAI_AGENT (CLI chat still works; SI picker will not list it).
"""
import argparse

from snowflake import snowpark

from relationalai.agent.cortex import (
    CortexAgentManager,
    DeploymentConfig,
    QueryCatalog,
    ToolRegistry,
    discover_imports,
)
from relationalai.config import SnowflakeConnection, create_config

AGENT_NAME = "nestle_diet"
DATABASE = "PK_NESTLE_DIET"
SCHEMA = "RAI_AGENT"
AGENT_SCHEMA = "SNOWFLAKE_INTELLIGENCE.AGENTS"  # set None to deploy into PK_NESTLE_DIET.RAI_AGENT
WAREHOUSE = "RAI_XS"


def _agent_location() -> str:
    return AGENT_SCHEMA or f"{DATABASE}.{SCHEMA}"


def _build_manager() -> CortexAgentManager:
    session: snowpark.Session = create_config().get_session(SnowflakeConnection)
    session.sql(f"CREATE SCHEMA IF NOT EXISTS {DATABASE}.{SCHEMA}").collect()
    return CortexAgentManager(
        session=session,
        config=DeploymentConfig(
            agent_name=AGENT_NAME,
            database=DATABASE,
            schema=SCHEMA,
            agent_schema=AGENT_SCHEMA,
            warehouse=WAREHOUSE,
            allow_preview=True,  # required for QueryCatalog (PREVIEW)
        ),
    )


def init_tools():
    from rai_code.manual import nestle_diet, demo_queries  # noqa: F401

    from . import queries

    return ToolRegistry().add(
        model=nestle_diet.model,
        description=(
            "Vegan diet/menu optimization for Marco, a busy startup executive "
            "training for marathons. Backed by real nutrition data (USDA "
            "FoodData Central, Open Food Facts) plus a synthesized recipe "
            "catalog with cost, CO2, and 16 nutrient targets. Answers: the "
            "naive cheapest day that fails nutrition (problem), the cheapest "
            "menu meeting every target (the optimized fix), and the same menu "
            "re-solved under a carbon cap (operator-added sustainability rule)."
        ),
        queries=QueryCatalog(
            queries.marco_naive_cheapest_day,
            queries.marco_optimal_menu,
            queries.marco_menu_under_carbon_cap,
            queries.marco_diet_commodities,
        ),
    )


def cmd_deploy(manager: CortexAgentManager) -> None:
    print(f"Deploying sprocs to {DATABASE}.{SCHEMA} and agent {AGENT_NAME} to {_agent_location()} ...")
    manager.deploy(init_tools=init_tools, imports=discover_imports(), extra_packages=["httpx"])
    print(manager.status())


def cmd_update(manager: CortexAgentManager) -> None:
    print(f"Updating stored procedures for {AGENT_NAME} ...")
    manager.update(init_tools=init_tools, imports=discover_imports(), extra_packages=["httpx"])
    print(manager.status())


def cmd_status(manager: CortexAgentManager) -> None:
    print(manager.status())


def cmd_chat(manager: CortexAgentManager, message: str) -> None:
    chat = manager.chat()
    response = chat.send(message)
    print(response.full_text())


def cmd_teardown(manager: CortexAgentManager) -> None:
    print(f"Tearing down agent {AGENT_NAME} from {_agent_location()} and sprocs from {DATABASE}.{SCHEMA} ...")
    print("WARNING: this permanently deletes SI conversation history.")
    manager.cleanup()
    print(manager.status())


def cmd_preflight(manager: CortexAgentManager) -> None:
    report = manager.preflight(init_tools=init_tools)
    print(report.format(config=manager.config))


def cmd_setup_sql(manager: CortexAgentManager, deployer_role: str, si_role: str) -> None:
    manager.print_setup_sql(deployer_role=deployer_role, si_role=si_role)


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage the nestle_diet Cortex agent lifecycle.")
    sub = parser.add_subparsers(dest="command")
    sub.required = True
    sub.add_parser("deploy", help="Create schema, stage, sprocs, and agent")
    sub.add_parser("update", help="Update sprocs without re-registering the agent")
    sub.add_parser("status", help="Print deployment status")
    sub.add_parser("preflight", help="Probe grants without deploying")
    setup_p = sub.add_parser("setup-sql", help="Emit a paste-ready GRANT block")
    setup_p.add_argument("--deployer-role", default="RAI_DEMO_NESTLE_DIET")
    setup_p.add_argument("--si-role", default="RAI_DEMO_NESTLE_DIET")
    chat_p = sub.add_parser("chat", help="Send a message to the deployed agent")
    chat_p.add_argument("message", help="Message to send")
    sub.add_parser("teardown", help="Remove all agent resources")

    args = parser.parse_args()
    manager = _build_manager()
    commands = {
        "deploy": lambda: cmd_deploy(manager),
        "update": lambda: cmd_update(manager),
        "status": lambda: cmd_status(manager),
        "chat": lambda: cmd_chat(manager, args.message),
        "teardown": lambda: cmd_teardown(manager),
        "preflight": lambda: cmd_preflight(manager),
        "setup-sql": lambda: cmd_setup_sql(manager, args.deployer_role, args.si_role),
    }
    commands[args.command]()


if __name__ == "__main__":
    main()
