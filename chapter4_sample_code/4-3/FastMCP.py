from mcp.server.fastmcp import FastMCP

# FastMCPサーバを初期化
mcp = FastMCP("Test Server")

# サンプルツール：体重と身長を受取り、BMIを計算するツール
@mcp.tool()
def calculate_bmi(weight_kg: float, height_m: float) -> float:
    """BMIを計算する際に用いる"""
    return weight_kg / (height_m**2)

# サンプルプロンプト：コードレビューを行うプロンプト
@mcp.prompt()
def review_code(code: str) -> str:
    return f"下記のコードをレビューしてください:\n\n{code}"

# サンプルリソース：アプリのConfigデータを提供するリソース
@mcp.resource("config://app")
def get_config() -> str:
    """Static configuration data"""
    return "App configuration data here"

if __name__ == "__main__":
    mcp.run(transport="stdio")