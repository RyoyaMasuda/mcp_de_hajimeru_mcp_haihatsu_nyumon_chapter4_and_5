# 非同期処理を行うためのライブラリをインポートします。
import asyncio
# JSON形式のデータを扱うためのライブラリをインポートします。
import json
# ログ出力を行うためのライブラリをインポートします。プログラムの動作状況を確認するのに使います。
import logging
# オペレーティングシステム（OS）の機能（環境変数の読み込みなど）を利用するためのライブラリをインポートします。
import os
# 非同期コンテキストマネージャを安全に管理するためのライブラリをインポートします。
from contextlib import AsyncExitStack
# 型ヒントを定義するためのライブラリをインポートします。コードの可読性と保守性を高めます。
from typing import Dict, List, Optional, Any
# .envファイルから環境変数を読み込むためのライブラリをインポートします。APIキーなどを安全に管理できます。
from dotenv import load_dotenv
# OpenAIのAPIと対話するためのライブラリをインポートします。
from openai import OpenAI
# OpenAI APIからの応答の型をインポートします。
from openai.types.responses import Response, ResponseFunctionToolCall
# データモデルを定義するためのライブラリをインポートします。データのバリデーション（検証）などに使います。
from pydantic import BaseModel
# MCP (Model Context Protocol) クライアントセッション、エラー、標準入出力サーバーパラメータをインポートします。
# これらはLLMがツールと通信するための基盤となります。
from mcp import ClientSession, McpError, StdioServerParameters
# MCPクライアントの標準入出力実装をインポートします。
from mcp.client.stdio import stdio_client
# MCPのツールの型定義をインポートします。
from mcp.types import Tool

# .envファイルから環境変数を読み込みます。
# これにより、APIキーなどの機密情報をコードに直接書き込まずに済みます。
load_dotenv()
# OpenAI APIキーを環境変数から取得します。
API_KEY = os.getenv("OPENAI_API_KEY")
# 使用するLLM（大規模言語モデル）のモデル名を定義します。
MODEL_NAME = "gpt-4.1"
# サーバー名とツール名を区切るための文字列を定義します。
TOOL_SEPARATOR = "__"

# ロギング設定を行います。
# level=logging.INFO: 情報レベル以上のメッセージをログに出力します。
# format: ログメッセージの表示形式を定義します。
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
# ロガーインスタンスを作成します。これを使ってログメッセージを出力します。
logger = logging.getLogger(__name__)

# MCPサーバーの設定を辞書形式で定義します。
# 各サーバーは、実行コマンドと引数を持っています。
RAW_CONFIG: Dict[str, dict] = {
    # 'fetch' サーバーの設定
    "fetch": {"command": "uvx", "args": ["mcp-server-fetch"]},
    # 'google_search' サーバーの設定
    "google_search": {
        "command": "uv", # 実行するコマンド
        "args": [ # コマンドに渡す引数
            "--directory", # サーバーのディレクトリを指定するオプション
            "/home/ryoyamasuda/Documents/mcp_de_hajimeru_mcp_haihatsu_nyumon_chapter4_and_5/servers/src", # Google検索サーバーのソースコードがあるディレクトリ
            "run", # uvコマンドのサブコマンド
            "server_google_search.py" # 実行するPythonスクリプト
        ], # ご自身の環境に合わせて修正（ここは特に重要です！）
    },
}

# MCPサーバーの情報を保持するためのPydanticモデルを定義します。
# これにより、サーバーの設定を構造化して扱えます。
class MCPServer(BaseModel):
    """単一のMCPサーバーインスタンスの定義。"""

    name: str # サーバーの名前
    command: str # サーバーを起動するためのコマンド
    args: List[str] # コマンドに渡す引数のリスト
    env: Optional[Dict[str, str]] = None # サーバーに渡す環境変数（オプション）
    session: Any = None # MCPクライアントセッションオブジェクト（実行時に設定されます）

def mcp_tool_to_openai_tool(tool: Tool, server_name: str) -> dict:
    """MCPのToolオブジェクトをOpenAIのFunction Callingスキーマに変換する。
    LLMがMCPツールを呼び出せるように、OpenAIが理解できる形式に変換します。
    """
    # サーバー名とツール名を組み合わせて、OpenAIが認識する一意なツール名を生成します。
    unique_name = f"{server_name}{TOOL_SEPARATOR}{tool.name}"
    return {
        "type": "function",
        "function": {
            "name": unique_name, # OpenAIに渡すツール名
            "description": tool.description, # ツールの説明（LLMがいつ使うべきかを判断するのに役立ちます）
            "parameters": tool.schema, # ツールの入力パラメータのスキーマ
        },
    }

async def init_servers(stack: AsyncExitStack, servers: Dict[str, MCPServer]) -> List[dict]:
    """初期化部：設定された全MCPサーバーを起動し、利用可能なツールを収集する。
    この関数は、MCPサーバーを起動し、それぞれのサーバーが提供するツールをOpenAI形式に変換して返します。
    """
    openai_tools: List[dict] = [] # OpenAI形式のツールを格納するリスト

    # 設定された各サーバーについて処理を行います。
    for server in servers.values():
        try:
            # MCPクライアントを起動し、標準入出力ストリーム（read, write）を取得します。
            # AsyncExitStackを使って、サーバーの起動と停止を適切に管理します。
            read, write = await stack.enter_async_context(
                stdio_client(
                    StdioServerParameters(
                        command=server.command, args=server.args, env=server.env
                    )
                )
            )
            # 取得したストリームを使ってMCPクライアントセッションを作成します。
            server.session = await stack.enter_async_context(ClientSession(read, write))

            # MCPセッションを初期化します。
            await server.session.initialize()
            # サーバーが提供するツールのリストを取得します。
            response = await server.session.list_tools()

            # ログに利用可能なツール名を出力します。
            logger.info(
                f"[{server.name}] available tools → {[t.name for t in response.tools]}"
            )

            # 取得したMCPツールをOpenAI形式に変換し、リストに追加します。
            for t in response.tools:
                openai_tools.append(mcp_tool_to_openai_tool(t, server.name))

        # MCPサーバーでエラーが発生した場合の処理（3.4節 パターンBのエラー処理）
        except McpError as e:
            # エラーメッセージをログに出力します。
            logger.error(
                f"MCP Error on server '{server.name}': {e.error.message} (Code: {e.error.code})"
            )
    return openai_tools

async def dispatch_tool_call(
    tool_call: ResponseFunctionToolCall, servers: Dict[str, MCPServer]) -> str:
    """LLMのツール呼び出し指示を解釈し、対応するMCPツールを実行する。
    LLMが特定のツールを呼び出すように指示した場合、この関数がそのツールを実際に実行します。
    """
    
    args = json.loads(tool_call.arguments)
    server_name, tool_name = tool_call.name.split(TOOL_SEPARATOR)
    session = servers[server_name].session

    logger.info(f"Calling tool '{tool_name}' on server '{server_name}'")
    result = await session.call_tool(name=tool_name, arguments=args)
    
    if result.isError:
        error_content = (result.content[0].text if result.content else "Unknown tool error")
        logger.warning(f"Tool '{tool_name}' returned an error: {error_content}")
        return f"Tool Error: {error_content}"

    logger.info(f"Tool '{tool_name}' executed successfully.")
    return str(result.content[0].text)

async def chat_loop(servers: Dict[str, MCPServer]) -> None:
    """対話制御部：ユーザーとの対話ループを管理し、LLMとMCPサーバーを連携される。
    この関数は、ユーザーからの入力を受け取り、LLMに渡して応答を生成し、
    必要に応じてMCPツールを呼び出す一連の処理を管理します。
    """
    client = OpenAI(api_key=API_KEY)

    async with AsyncExitStack() as stack:
        tools = await init_servers(stack, servers)
        previous_id: Optional[str] = None

        while True:
            user_text = await asyncio.to_thread(input, "You: ")
            if user_text.strip().lower() in {"exit", "quit"}:
                break
            
            call_kwargs = {
                "model": MODEL_NAME,
                "input": [{"role": "user", "content": user_text}],
                "tools": tools,
            }

            if previous_id:
                call_kwargs["previous_response_id"] = previous_id

            response: Response = client.response.create(**call_kwargs)

            while any(item.type == "function_call" for item in response.output):
                tool_outputs = []
                for tool_call in response.output:
                    if tool_call.type != "function_call":
                        continue

                    tool_output = await dispatch_tool_call(tool_call, servers)
                    tool_outputs.append(
                        {
                            "type": "function_call_output",
                            "call_id": tool_call.call_id,
                            "output": tool_output,
                        }
                    )

                logger.info(f"Submitting tool outputs: {len(tool_outputs)}")
                response = client.responses.create(
                    model=MODEL_NAME,
                    previous_response_id=response.id,
                    input=tool_outputs,
                    tools=tools,
                )

                logger.info(f"Model response: {response}")

            
            previous_id = response.id
            print(f"Assistant: {response.output_text}\n")

def build_servers() -> Dict[str, MCPServer]:
    """MCPサーバーを構築する。
    """
    return {
        name: MCPServer(**config)
        for name, config in RAW_CONFIG.items()
    }

def main() -> None:
    """メイン関数：プログラムのエントリーポイント。
    MCPサーバーを初期化し、ユーザーとの対話ループを開始します。
    """
    servers = build_servers()
    asyncio.run(chat_loop(servers))

if __name__ == "__main__":
    main()