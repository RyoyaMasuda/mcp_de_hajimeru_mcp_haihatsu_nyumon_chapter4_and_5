from mcp.server.fastmcp import FastMCP

# FastMCPサーバを初期化
mcp = FastMCP("Test Server")


@mcp.tool()
def calculate_bmi(weight_kg: float, height_m: float) -> float:
    """BMIを計算する際に用いる"""
    return weight_kg / (height_m**2)


@mcp.prompt()
def review_code(code: str) -> str:
    return f"下記のコードをレビューしてください:\n\n{code}"

@mcp.resource("config://app")
def get_config() -> str:
    """Static configuration data"""
    return "App configuration here"

if __name__ == "__main__":
    mcp.run(transport="stdio")