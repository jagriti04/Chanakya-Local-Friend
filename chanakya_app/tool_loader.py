from typing import List
from langchain_core.tools.render import render_text_description
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from .app_setup import app
from .config_loader import load_mcp_config_internal, MCP_CONFIG_FILENAME

CACHED_MCP_TOOLS: List[BaseTool] = []
MCP_TOOLS_LOADED_FLAG = False
mcp_tool_descriptions_for_llm: str = "No tools loaded yet."
mcp_tool_names_for_llm: str = "No tool names loaded yet."

async def load_all_mcp_tools_async(force_reload=False) -> List[BaseTool]:
    global CACHED_MCP_TOOLS, MCP_TOOLS_LOADED_FLAG, mcp_tool_descriptions_for_llm, mcp_tool_names_for_llm
    if MCP_TOOLS_LOADED_FLAG and not force_reload:
        app.logger.info("Returning cached MCP tools for Chanakya.")
        return CACHED_MCP_TOOLS

    app.logger.info("Loading MCP configuration and all tools directly for Chanakya (ASYNCHRONOUSLY)...")
    mcp_servers = load_mcp_config_internal(MCP_CONFIG_FILENAME)
    cfg_local = {}
    if mcp_servers:
        for name, details in mcp_servers.items():
            server_config_for_client = {
                "command": details["command"], "args": details["args"],
                "transport": details.get("transport", "stdio")
            }
            if "env" in details and isinstance(details["env"], dict):
                server_config_for_client["env"] = details["env"]
            cfg_local[name] = server_config_for_client

    if not cfg_local:
        app.logger.warning("MCP client config is effectively empty. No tools will be loaded.")
        CACHED_MCP_TOOLS = []
        MCP_TOOLS_LOADED_FLAG = True
        mcp_tool_descriptions_for_llm = "No specialized tools available."
        mcp_tool_names_for_llm = ""
        return []

    app.logger.info(f"Initializing MCPClient for Chanakya with processed config: {cfg_local}")
    client = MultiServerMCPClient(cfg_local)
    app.logger.info("Loading all MCP tools via client for Chanakya (ASYNCHRONOUSLY)...")

    tools: List[BaseTool] = []
    try:
        tools = await client.get_tools()
        app.logger.info(f"Successfully fetched {len(tools)} tools from MCP client asynchronously.")
    except Exception as e_gen:
        app.logger.error(f"General error during client.get_tools() (async): {e_gen}", exc_info=True)
        tools = []

    CACHED_MCP_TOOLS = tools
    MCP_TOOLS_LOADED_FLAG = True

    if CACHED_MCP_TOOLS:
        mcp_tool_descriptions_for_llm = render_text_description(CACHED_MCP_TOOLS)
        mcp_tool_names_for_llm = ", ".join([t.name for t in CACHED_MCP_TOOLS])
        app.logger.info(f"Loaded {len(CACHED_MCP_TOOLS)} MCP tools for Chanakya: {[t.name for t in CACHED_MCP_TOOLS]}")
        app.logger.info(f"Tools descriptions: {mcp_tool_descriptions_for_llm}")
    else:
        mcp_tool_descriptions_for_llm = "No specialized tools are currently available."
        mcp_tool_names_for_llm = ""
        app.logger.warning("No MCP tools were loaded for Chanakya.")

    return CACHED_MCP_TOOLS
