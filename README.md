rootに.envファイルのAPIキーを設定すること。

.envファイルのサンプル

```env
OPENAI_API_KEY = "asdf"
GOOGLE_CSE_API_KEY = "asdf"
GOOGLE_CSE_ID = "asdf"
```


### google api を設定する方法

1. Create or select a Google Cloud project.	console.cloud.google.com
2. In APIs & Services → Library enable “Custom Search API (customsearch.googleapis.com)”.	
3. Open APIs & Services → Credentials → Create credentials → API key. Copy the key (we’ll call it GOOGLE_CSE_API_KEY).	
4. Visit the Programmable Search Engine control panel, press Create Search Engine, choose “Search the entire web” (or restrict to certain domains), and save.	
5. On the engine’s Overview page copy the Search engine ID (the “cx” value, we’ll call it GOOGLE_CSE_ID).	

The API gives you 100 queries per day free; extra usage costs US$ 5 per 1 000 requests up to 10 000/day