# 概要
mcpのホストとサーバの実装サンプルコード
### ホスト
1. agent_chat_with_google_search.py
  * mcpサーバのfetchと、google searchを基に回答するcli基盤のチャット
2. agent_company_analyze.py
  * 日本の企業を分析するAIエージェント。必要情報が揃うまでにループするので注意が必要。少しバグあり

### MCPサーバ
1. server_google_search.py
  * 公式google apiを使ったgoogle検索サーバ。google 検索の上位5個を返す

# 環境設定方法
### 1. google api を設定する

1. Create or select a Google Cloud project.	console.cloud.google.com
2. In APIs & Services → Library enable “Custom Search API (customsearch.googleapis.com)”.	
3. Open APIs & Services → Credentials → Create credentials → API key. Copy the key (we’ll call it GOOGLE_CSE_API_KEY).	
4. Visit the Programmable Search Engine control panel, press Create Search Engine, choose “Search the entire web” (or restrict to certain domains), and save.	
5. On the engine’s Overview page copy the Search engine ID (the “cx” value, we’ll call it GOOGLE_CSE_ID).	

The API gives you 100 queries per day free; extra usage costs US$ 5 per 1 000 requests up to 10 000/day

### 2. .evnファイルを作成する

rootに.envファイルのAPIキーを設定すること。

.envファイルのサンプル

```env
OPENAI_API_KEY = "asdf"
GOOGLE_CSE_API_KEY = "asdf"
GOOGLE_CSE_ID = "asdf"
```


### 実行方法
 uv run .\agent_chat_with_google_search.py

他のホストも同様にuv runで実行する