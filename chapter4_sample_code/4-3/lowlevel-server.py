import anyio
from pydantic import AnyUrl

from mcp.server.lowlevel import Server
import mcp.types as types
from mcp.server.stdio import stdio_server

# サーバを初期化
server = Server("Test Server")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """利用可能なツールの一覧を返す"""
    return [
        types.Tool(
            name="fetch_website",
            description="Webサイトを取得してその内容を返す",
            inputSchema={
                "type": "object",
                "required": ["url"],
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "取得するURL",
                    }
                },
            },
        ),
        types.Tool(
            name="check_status",
            description="指定されたURLのHTTPステータスコードを確認する",
            inputSchema={
                "type": "object",
                "required": ["url"],
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "ステータスを確認するURL",
                    }
                },
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict
) -> list[types.TextContent | types.ImageContent | types.AudioContent | types.EmbeddedResource]:
    """具体的なツールの実行処理"""
    if name == "fetch_website":  # Webサイトを取得してその内容を返す
        if "url" not in arguments:
            raise ValueError("Missing required argument 'url'")
        # ここで実際のWebサイト取得処理を実装
        page_text = "This is a sample content from the website."  # 仮の内容
        return [types.TextContent(type="text", text=f"取得したWebサイトの内容: {page_text}")]

    elif name == "check_status":  # 指定されたURLのHTTPステータスコードを返す
        if "url" not in arguments:
            raise ValueError("Missing required argument 'url'")
        # ここで実際のステータス確認処理を実装
        status = 200  # 仮のステータスコード
        return [types.TextContent(type="text", text=f"ステータスコード: {status} OK for {arguments['url']}")]
    else:
        raise ValueError(f"Unknown tool: {name}")


@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    """利用可能なプロンプトの一覧を返す"""
    return [
        types.Prompt(
            name="review_code",
            description="コードレビュー用のプロンプト",
            arguments=[types.PromptArgument(name="code", description="レビュー対象のコード", required=True)],
        )
    ]


@server.get_prompt()
async def handle_get_prompt(name: str, arguments: dict[str, str] | None) -> types.GetPromptResult:
    """指定されたプロンプトの具体的な内容を生成"""
    if name == "review_code" and arguments and "code" in arguments:
        return types.GetPromptResult(
            description="コードレビュー用プロンプト",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(type="text", text=f"下記のコードをレビューしてください:\n\n{arguments['code']}"),
                )
            ],
        )
    else:
        raise ValueError(f"Unknown prompt: {name}")


@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """利用可能なリソースの一覧を返す"""
    return [
        types.Resource(
            uri="config://app", name="App Configuration", description="アプリケーションの設定情報", mimeType="text/plain"
        )
    ]


@server.read_resource()
async def handle_read_resource(uri: AnyUrl) -> str | bytes:
    """指定されたリソースの内容を返す"""
    if str(uri) == "config://app":
        return "App configuration here"
    else:
        raise ValueError(f"Unknown resource: {uri}")


async def main():
    # stdio_server()は標準入出力ストリームのペアを返す
    # read_stream: クライアントからのメッセージ受信用
    # write_stream: クライアントへのメッセージ送信用
    async with stdio_server() as (read_stream, write_stream):
        # 初期化オプションには、サーバー名・バージョン・機能情報が含まれる
        initialization_options = server.create_initialization_options()

        # サーバーセッションを開始（ライフサイクル管理とメッセージ処理を含む）
        await server.run(
            read_stream,
            write_stream,
            initialization_options,
        )


if __name__ == "__main__":
    # 非同期ランタイムでメイン関数を実行
    anyio.run(main)
