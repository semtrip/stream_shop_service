class Headers:
    headers_pool = [
    {  # 1
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,\
image/avif,image/webp,image/apng,*/*;q=0.8",
        "Referer": "https://www.google.com/",
        "Origin": "https://www.google.com",
        "Connection": "keep-alive",
        "DNT": "1",
        "Sec-CH-UA": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site"
    },
    {  # 2
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) \
AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Accept": "text/html,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://duckduckgo.com/",
        "Origin": "https://duckduckgo.com",
        "Connection": "keep-alive",
        "DNT": "1",
        "Sec-CH-UA": '"Safari";v="17", "Not.A/Brand";v="99"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site"
    },
    {  # 3
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:125.0) \
Gecko/20100101 Firefox/125.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.bing.com/",
        "Origin": "https://www.bing.com",
        "Connection": "keep-alive",
        "DNT": "0",
        "Sec-CH-UA": '"Firefox";v="125", "Gecko";v="125", "Not:A-Brand";v="99"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site"
    },
    {  # 4
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) \
AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://m.facebook.com/",
        "Origin": "https://m.facebook.com",
        "Connection": "keep-alive",
        "DNT": "1",
        "Sec-CH-UA": '"Safari";v="17", "Not.A/Brand";v="99"',
        "Sec-CH-UA-Mobile": "?1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site"
    },
    {  # 5
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
AppleWebKit/537.36 (KHTML, like Gecko) Edg/125.0.0.0 Chrome/124.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Referer": "https://twitter.com/",
        "Origin": "https://twitter.com",
        "Connection": "keep-alive",
        "DNT": "0",
        "Sec-CH-UA": '"Microsoft Edge";v="125", "Chromium";v="125", "Not.A/Brand";v="99"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site"
    },
    {  # 6
        "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S918B) \
AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,image/avif,image/webp,*/*;q=0.8",
        "Referer": "https://news.ycombinator.com/",
        "Origin": "https://news.ycombinator.com",
        "Connection": "keep-alive",
        "DNT": "1",
        "Sec-CH-UA": '"Chromium";v="124", "Not.A/Brand";v="99"',
        "Sec-CH-UA-Mobile": "?1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site"
    },
    {  # 7
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0_0) \
AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Referer": "https://www.reddit.com/",
        "Origin": "https://www.reddit.com",
        "Connection": "keep-alive",
        "DNT": "0",
        "Sec-CH-UA": '"Chromium";v="123", "Not.A/Brand";v="99"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site"
    },
    {  # 8
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 \
(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Referer": "https://github.com/",
        "Origin": "https://github.com",
        "Connection": "close",
        "DNT": "1",
        "Sec-CH-UA": '"Chromium";v="124", "Not.A/Brand";v="99"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin"
    },
    {  # 9
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) \
Gecko/20100101 Firefox/124.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://t.co/",
        "Origin": "https://t.co",
        "Connection": "keep-alive",
        "DNT": "1",
        "Sec-CH-UA": '"Firefox";v="124", "Gecko";v="124"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site"
    },
    {  # 10
        "User-Agent": "Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) \
AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.instagram.com/",
        "Origin": "https://www.instagram.com",
        "Connection": "keep-alive",
        "DNT": "0",
        "Sec-CH-UA": '"Safari";v="17", "Not.A/Brand";v="99"',
        "Sec-CH-UA-Mobile": "?1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site"
    },
    {  # 11
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,*/*;q=0.8",
        "Referer": "https://www.twitch.tv/",
        "Origin": "https://www.twitch.tv",
        "Connection": "keep-alive",
        "DNT": "1",
        "Sec-CH-UA": '"Chromium";v="122", "Not.A/Brand";v="99"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-Fetch-Dest": "image",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-origin"
    },
    {  # 12
        "User-Agent": "Mozilla/5.0 (X11; Fedora; Linux x86_64) \
AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Referer": "https://yandex.ru/search/",
        "Origin": "https://yandex.ru",
        "Connection": "keep-alive",
        "DNT": "0",
        "Sec-CH-UA": '"Chromium";v="125", "Not.A/Brand";v="99"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site"
    },
    {  # 13
        "User-Agent": "Mozilla/5.0 (Macintosh; Apple Silicon; macOS 14_0) \
AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
        "Accept": "text/html,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://developer.apple.com/",
        "Origin": "https://developer.apple.com",
        "Connection": "close",
        "DNT": "1",
        "Sec-CH-UA": '"Safari";v="17", "Not.A/Brand";v="99"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin"
    },
    {  # 14
        "User-Agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8) \
AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "Accept": "application/json,*/*;q=0.8",
        "Referer": "https://reddit.com/",
        "Origin": "https://reddit.com",
        "Connection": "keep-alive",
        "DNT": "0",
        "Sec-CH-UA": '"Chromium";v="124", "Not.A/Brand";v="99"',
        "Sec-CH-UA-Mobile": "?1",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site"
    },
    {  # 15
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
Gecko/20100101 Firefox/123.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://medium.com/",
        "Origin": "https://medium.com",
        "Connection": "keep-alive",
        "DNT": "1",
        "Sec-CH-UA": '"Firefox";v="123", "Gecko";v="123"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site"
    },
    {  # 16
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/plain,*/*;q=0.8",
        "Referer": "https://www.linkedin.com/",
        "Origin": "https://www.linkedin.com",
        "Connection": "keep-alive",
        "DNT": "0",
        "Sec-CH-UA": '"Chromium";v="121", "Not.A/Brand";v="99"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site"
    },
    {  # 17
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_6) \
AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Referer": "https://www.youtube.com/",
        "Origin": "https://www.youtube.com",
        "Connection": "keep-alive",
        "DNT": "1",
        "Sec-CH-UA": '"Chromium";v="120", "Not.A/Brand";v="99"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin"
    },
    {  # 18
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 \
(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.wikipedia.org/",
        "Origin": "https://www.wikipedia.org",
        "Connection": "close",
        "DNT": "0",
        "Sec-CH-UA": '"Chromium";v="119", "Not.A/Brand";v="99"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site"
    },
    {  # 19
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6_1 like Mac OS X) \
AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://m.twitch.tv/",
        "Origin": "https://m.twitch.tv",
        "Connection": "keep-alive",
        "DNT": "1",
        "Sec-CH-UA": '"Safari";v="16", "Not.A/Brand";v="99"',
        "Sec-CH-UA-Mobile": "?1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin"
    },
    {  # 20
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Referer": "https://r.search.yahoo.com/",
        "Origin": "https://r.search.yahoo.com",
        "Connection": "keep-alive",
        "DNT": "0",
        "Sec-CH-UA": '"Chromium";v="118", "Not.A/Brand";v="99"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site"
    }
]
