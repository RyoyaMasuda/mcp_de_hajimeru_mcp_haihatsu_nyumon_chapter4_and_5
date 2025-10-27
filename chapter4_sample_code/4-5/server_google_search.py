from re import M
from mcp.server.fastmcp import FastMCP, Context
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from rich import print

import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GOOGLE_CSE_API_KEY")
CX_ID = os.getenv("GOOGLE_CSE_ID")

mcp = FastMCP("google_search_server")

@mcp.tool()
async def google_search(query: str, ctx: Context) -> str:
    """
    指定されたクエリでGoogle検索を行い、最初の5件の結果を返します。
    日本からの検索として扱い、日本語の結果を優先します。

    Args:
        query (str): 検索クエリ
        ctx (Context): ロギング用のMCPコンテキスト
    """

    if not query or not query.strip():
        raise ValueError("検索クエリを入力してください")
    
    if len(query) > 100:
        raise ValueError("検索クエリは100文字以内にして")

    if not API_KEY or not CX_ID:
        raise Exception("apiキーが設定されてない。")

    await ctx.info(f"google検索を実行: '{query}'")
    

    # 検索実施
    try:
        # Google Custom Search APIの呼び出し
        service = build("customsearch", "v1", developerKey=API_KEY)
        resp = (
            service.cse().list(
                q=query,
                cx=CX_ID,
                num=5, # 上位5件を返す
                gl="jp", # 日本からの検索
                lr="lang_ja", # 日本語優先
            ).execute()
        )
        

    except HttpError as e:
        if e.resp.status == 403:
            await ctx.error("api利用制限エラー")
            raise Exception("googleの検索apiの利用制限に達した。1日100回まで")
        else:
            await ctx.error(f"apiエラー: '{str(e)}'")
            raise Exception("google検索apiでエラー発生。しばらく待て")
    except Exception as e:
        await ctx.error(f"検索エラー: {str(e)}")
        raise Exception("検索中にエラー。インターネット接続を確認しろ")
    
    print(f"type(resp): {type(resp)}")
    print(resp)
    items = resp.get("items")

    if not items:
        return "検索結果なし"

    cleaned = []
    for rank, it in enumerate(items, 1):
        meta = (it.get("pagemap", {}).get("metatags") or [{}])[0]
        published = meta.get("article:published_time") or meta.get("og:update_time")

        cleaned.append(
            {
                "rank": rank,
                "title": it["title"],
                "snippet": it["snippet"],
                "url": it["link"],
                "domain": it.get("displayLink"),
                "published_at": published
            }
        )
    
    await ctx.info(f"検索完了: {len(cleaned)}件の結果")

    return str(cleaned)

if __name__ == "__main__":
    mcp.run(transport="stdio")