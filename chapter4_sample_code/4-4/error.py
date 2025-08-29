import re
from mcp.server.fastmcp import FastMCP

# FastMCPサーバを初期化
mcp = FastMCP("Test Server") 

# ダミーの天気API呼び出し関数
async def call_weather_api(location: str) -> str:
    return "Sunny"

# ダミーの例外クラス
class SomeAPIClientError(Exception):
    pass

@mcp.tool()
async def get_weather(location: str) -> str:
    # location引数が英語で構成されているかを判定
    if not re.fullmatch(r"[A-Za-z\s]+", location):
        raise ValueError("場所は英語で指定してください")
        # ValueErrorを送出すると、isError=trueとなったリザルトオブジェクトがクライアントに返される

    try:
        # 天気APIを呼び出す
        weather = await call_weather_api(location)
        return f"{location} の天気は {weather} です"

    except SomeAPIClientError:
        # API呼び出し中に接続エラーなどが発生した場合
        raise Exception("天気APIに接続できません")
        # 通常の例外も自動的にisError=trueとなったリザルトオブジェクトとしてクライアントに返される
