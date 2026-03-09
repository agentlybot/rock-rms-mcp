from mcp.server.fastmcp import FastMCP

from rock_rms_mcp.client import RockClient

mcp = FastMCP("rock-rms")
rock = RockClient()


@mcp.tool()
def ping() -> str:
    """Check connectivity to Rock RMS. Returns OK if authenticated."""
    rock.get("People?$top=1&$select=Id")
    return "OK — connected to Rock RMS"


def main():
    mcp.run(transport="stdio")
