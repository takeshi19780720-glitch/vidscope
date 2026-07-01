# Verdent – YouTube API Services Compliance Screencast
## Narration Script (English) · Target Length: 5–8 minutes

---

### SECTION 1 — Introduction (0:00 – 0:45)

> *[Show the browser pointing to http://localhost:8000/?duration=short]*

"Hello, and welcome to this compliance review screencast for Verdent —
a YouTube video search and analysis tool built on top of the YouTube Data API v3.

This recording demonstrates how our application accesses, displays, and handles
data obtained from YouTube's API Services in accordance with YouTube's API Services
Terms of Service and Developer Policies.

Let me walk you through the main features."

---

### SECTION 2 — Application Overview (0:45 – 1:30)

> *[Slowly scroll the page top to bottom to show the full UI]*

"Verdent is a single-page web application served by a FastAPI back-end.
Users can search for YouTube videos by keyword, apply filters such as video duration,
publication date, category, language, and region — and immediately see rich analytics
for the top results.

All data displayed in this application comes exclusively from the YouTube Data API v3.
No data is scraped or obtained through any unofficial channel."

---

### SECTION 3 — Keyword Search Demo (1:30 – 2:30)

> *[Type "gaming" in the search box; the duration filter is already set to "short"
>   because the URL contains ?duration=short]*

"Let me demonstrate a live search.
I'll type the keyword 'gaming' and hit Search.

The application issues a request to our back-end at /api/search.
The back-end calls the YouTube Data API search.list endpoint with:
  - the keyword,
  - video type restricted to 'video',
  - duration filter set to 'short' (under 4 minutes),
  - results ordered by view count,
  - and a region code of 'US' by default.

The search.list call consumes 100 quota units.
The back-end then calls videos.list in batches of up to 50 IDs per request —
consuming only 1 quota unit per batch — to retrieve full statistics for each video."

> *[Wait for results to load and appear on screen]*

"The results are now displayed.
Each card shows the video thumbnail, title, channel name, and key metrics."

---

### SECTION 4 — Search Results & Analytics (2:30 – 4:00)

> *[Point to the results list; scroll slowly to show cards]*

"For every video in the top-10 results, Verdent displays the following data,
all sourced directly from the YouTube Data API:

  — Thumbnail: from the video's snippet.thumbnails field
  — Title: from snippet.title
  — Channel name: from snippet.channelTitle
  — Subscriber count: from a channels.list call using statistics.subscriberCount
  — View count: from statistics.viewCount
  — Like count: from statistics.likeCount
  — Duration: parsed from contentDetails.duration (ISO 8601 format)
  — Publication date: from snippet.publishedAt

Two calculated metrics are derived from this API data:
  — Engagement Rate (ENG%): calculated as viewCount ÷ subscriberCount,
    giving a sense of how well the video resonates with the channel's audience.
  — Estimated Revenue: a rough estimate based on industry-standard CPM ranges,
    presented as a reference only and clearly labelled as an estimate."

> *[Scroll down to show any chart or trend section if visible]*

"The trend analysis graphs visualise the distribution of views, engagement rates,
and publication dates across the result set — helping users understand market
patterns at a glance.

All of this data is presented in real time, directly from the API response.
No data is permanently stored in a database."

---

### SECTION 5 — API Usage & Quota Management (4:00 – 5:30)

> *[Open the browser DevTools Network tab or point to a quota indicator in the UI if present]*
> *[Navigate to http://localhost:8000/api/quota in a new tab to show the quota JSON]*

"Let me highlight the API call optimisation built into the application.

First, **quota awareness**: the application tracks quota consumption in memory.
Each search.list call costs 100 units.
Each videos.list call costs 1 unit per batch of up to 50 videos.
Each channels.list call also costs 1 unit per batch of up to 50 channels.
The daily quota limit of 10,000 units is respected and monitored via the /api/quota endpoint,
which you can see returning the current used and remaining units."

> *[Switch back to the main app tab and perform the same search again]*

"Second, **server-side caching**: results are cached for 30 minutes using an in-memory
LRU-style cache keyed by the search parameters.
If I search for 'gaming' again with the same filters, the application serves the cached
response immediately — zero additional API calls are made.
This dramatically reduces quota consumption for repeated queries."

> *[Show the second search completing instantly]*

"Third, **API key rotation**: the application supports multiple API keys.
If one key's quota is exhausted or a 403 error is returned, the client automatically
rotates to the next available key without interrupting the user experience."

---

### SECTION 6 — Data Display & Attribution (5:30 – 6:15)

> *[Click on a video card to show the detail view / channel info panel if available]*

"Every video result includes a direct link back to the original video on YouTube.
Clicking the video title or thumbnail opens the video on YouTube.com,
ensuring users can always access the authoritative source.

Channel information — including subscriber counts and recent uploads —
is also obtained via the YouTube Data API channels.list endpoint,
and similarly cached for 30 minutes to minimise redundant calls."

---

### SECTION 7 — End-User Benefits & Compliance Summary (6:15 – 7:15)

> *[Return to the main search results view]*

"Verdent is designed to help content creators and marketers with:
  — **Market research**: identify high-performing videos in any niche
  — **Revenue estimation**: gauge monetisation potential based on engagement data
  — **Competitive analysis**: compare channel performance across multiple creators
  — **Trend identification**: spot patterns in publication timing and view velocity

All of these use cases rely solely on the public data available through the YouTube Data API v3.

In summary:
  — We only call the YouTube Data API through official REST endpoints.
  — We do not scrape, cache beyond API-permitted durations, or redistribute raw API data.
  — All data is displayed in an aggregated, analytical context — not as a substitute for YouTube.
  — Every video and channel links back to YouTube.
  — Quota usage is tracked, capped, and minimised through caching and batching.

Thank you for reviewing Verdent's YouTube API Services compliance demonstration."

---

### SECTION 8 — Sign-off (7:15 – 7:30)

"This concludes the Verdent compliance screencast.
For any questions regarding our API usage, please refer to the source code
available in the project repository or contact the development team directly."

---
*End of narration script.*
