import asyncio
import json
import logging
import os
from contextlib import AsyncExitStack
from typing import Dict, List, Optional, Any

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.responses import Response, ResponseFunctionToolCall
from pydantic import BaseModel

from mcp import ClientSession, McpError, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool

# --- APIキーを.envファイルから読み込む ---
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")

# --- ロギング設定を追加 ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# --- 定数 ---
MODEL_NAME = "gpt-4.1"
TOOL_SEPARATOR = "__"

# --- MCPサーバー設定 ---
RAW_CONFIG: Dict[str, dict] = {
    "fetch": {"command": "uvx", "args": ["mcp-server-fetch"]},
    "google_search": {
        "command": "uv",
        "args": ["--directory", "/path/to/your/project/servers/src", "run", "server_google_search.py"], # ご自身の環境に合わせて修正
    },
}


class MCPServer(BaseModel):
    """単一のMCPサーバーインスタンスの定義。"""

    name: str
    command: str
    args: List[str]
    env: Optional[Dict[str, str]] = None
    session: Any = None


def mcp_tool_to_openai_tool(tool: Tool, server_name: str) -> dict:
    """MCPのToolオブジェクトをOpenAIのFunction Callingスキーマに変換する。"""
    unique_name = f"{server_name}{TOOL_SEPARATOR}{tool.name}"
    return {
        "type": "function",
        "name": unique_name,
        "description": tool.description,
        "parameters": tool.inputSchema,
    }


async def init_servers(
    stack: AsyncExitStack, servers: Dict[str, MCPServer]
) -> List[dict]:
    """初期化部：設定された全MCPサーバーを起動し、利用可能なツールを収集する。"""
    openai_tools: List[dict] = []

    for server in servers.values():
        try:
            read, write = await stack.enter_async_context(
                stdio_client(
                    StdioServerParameters(
                        command=server.command, args=server.args, env=server.env
                    )
                )
            )
            server.session = await stack.enter_async_context(ClientSession(read, write))

            await server.session.initialize()
            response = await server.session.list_tools()

            logger.info(
                f"[{server.name}] available tools → {[t.name for t in response.tools]}"
            )

            for t in response.tools:
                openai_tools.append(mcp_tool_to_openai_tool(t, server.name))

        # --- 3.4節 パターンBのエラー処理 ---
        except McpError as e:
            logger.error(
                f"MCP Error on server '{server.name}': {e.error.message} (Code: {e.error.code})"
            )

    return openai_tools


async def dispatch_tool_call(
    tool_call: ResponseFunctionToolCall, servers: Dict[str, MCPServer]
) -> str:
    """LLMのツール呼び出し指示を解釈し、対応するMCPツールを実行する。"""
    args = json.loads(tool_call.arguments)
    server_name, tool_name = tool_call.name.split(TOOL_SEPARATOR)
    session = servers[server_name].session

    logger.info(f"Calling tool '{tool_name}' on server '{server_name}'")
    result = await session.call_tool(name=tool_name, arguments=args)

    if result.isError:
        error_content = (
            result.content[0].text if result.content else "Unknown tool error"
        )
        logger.warning(f"Tool '{tool_name}' returned an error: {error_content}")
        return f"Tool Error: {error_content}"

    logger.info(f"Tool '{tool_name}' executed successfully.")
    return str(result.content[0].text)


async def chat_loop(servers: Dict[str, MCPServer]) -> None:
    """対話制御部：ユーザーとの対話ループを管理し、LLMとMCPサーバーを連携される。"""
    client = OpenAI(api_key=API_KEY)

    async with AsyncExitStack() as stack:
        tools = await init_servers(stack, servers)
        previous_id: Optional[str] = None

        while True:
            # ユーザーの入力。 "exit" または "quit" で終了。
            user_text = await asyncio.to_thread(input, "You: ")
            if user_text.strip().lower() in {"exit", "quit"}:
                break
            
            # MCPツールをLLMに渡すための引数を準備
            call_kwargs = {
                "model": MODEL_NAME,
                "input": [{"role": "user", "content": user_text}],
                "tools": tools,
            }

            # OpenAIのresponses APIではprevious_idでチャット履歴を管理できる
            if previous_id:
                call_kwargs["previous_response_id"] = previous_id
            
            # 初期のリクエストを送信
            response: Response = client.responses.create(**call_kwargs)

            # LLMがツール呼び出しを行う場合、それらを処理して結果を再送信
            while any(
                (item.type == "function_call") for item in response.output
            ):
                # MCPツールを呼び出し、その出力を収集
                # 複数回のツール呼び出しに対応
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


def build_servers(raw: Dict[str, dict]) -> Dict[str, MCPServer]:
    """RAW_CONFIGからMCPServerオブジェクトを構築する。"""
    return {name: MCPServer(name=name, **cfg) for name, cfg in raw.items()}


def main() -> None:
    servers = build_servers(RAW_CONFIG)
    asyncio.run(chat_loop(servers))


if __name__ == "__main__":
    main()
