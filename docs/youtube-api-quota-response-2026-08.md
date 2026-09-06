Subject: Re: YouTube Data API Quota Review – Project 484828457875

---

Dear YouTube API Review Team,

Thank you for reaching out regarding the quota calculation update. Below is the requested information for **Project 484828457875** (VidScope).

---

**1. API Endpoints and Expected Usage**

VidScope is a **read-only** application. No write-type APIs (e.g., `videos.insert`, `playlists.insert`) are used.

| Endpoint | Purpose | Calls per User Search | Quota Cost |
|---|---|---|---|
| `search.list` | Keyword-based video search | 1 call (2 calls when "normal" duration filter is applied, using medium + long separately) | 1 per call (independent bucket) |
| `videos.list` | Fetch video details (snippet, statistics, contentDetails) in batches of up to 50 | 1 call per search (default 10 results) | 1 unit per call (shared pool) |
| `channels.list` | Fetch subscriber counts; channel IDs are deduplicated and batched into a single request | 1 call per search | 1 unit per call (shared pool) |
| `playlistItems.list` | Fetch latest videos on a channel detail page (used only on channel detail page) | 1 call per channel page view | 1 unit per call (shared pool) |

**Typical API calls per user search action:**
- Standard search: `search.list` ×1 + `videos.list` ×1 + `channels.list` ×1 = **3 calls / 3 units**
- Search with "normal" duration filter: `search.list` ×2 + `videos.list` ×1 + `channels.list` ×1 = **4 calls / 3 units**

**Channel detail page view:**
- `channels.list` ×1 + `playlistItems.list` ×1 + `videos.list` ×1 = **3 units** (shared pool)

---

**2. Estimated API Call Volumes**

**Important distinction: not all page views trigger API calls.**

VidScope consists of two distinct types of content:

- **Blog articles** (`/blog/*`, 6 articles) — static SEO content. These pages make **zero YouTube API calls**. Readers browse the articles without any interaction with the YouTube Data API.
- **Landing page, privacy policy, terms of service, and contact page** — similarly, **no API calls** are made on these pages.
- **The `/app` page** — this is the only page where users perform searches and YouTube API calls are made.

**Traffic breakdown based on peak-day figures (analytics dashboard data):**

The following estimates are based on the **peak day observed** (75 PV/day in the past week), not a monthly average. Since the YouTube Data API quota resets daily, peak-day figures are the appropriate basis for quota assessment.

- Peak-day total site PV: **75 page views**
- Bot traffic excluded: `/wp-admin/install.php` and `/wp-login.php` accounted for a combined 1,169 cumulative PVs out of 7,928 total (≈15%), and are excluded from the estimate below
- `/app` page share of bot-filtered traffic: approximately **5–10%** (cumulative data: 385 `/app` PVs out of ~6,759 bot-filtered PVs ≈ 5.7%)
- **Peak-day `/app` page views: approximately 4–8 visits**

**Estimated peak-day API usage:**

Assumed usage per `/app` visit: **2–3 searches + occasional channel page views**.

| Metric | Estimate | Quota Limit | Headroom |
|---|---|---|---|
| `/app` visits on peak day | 4–8 | — | — |
| `search.list` calls (peak day) | ~8–24 calls | 100 calls/day | >75% remaining |
| Shared pool usage (peak day) | ~16–48 units | 10,000 units/day | >99% remaining |

These estimates include a conservative buffer for channel detail page views and the "normal" duration filter case (which uses 2 `search.list` calls instead of 1).

---

**3. Current and Projected User Traffic**

VidScope is currently a personal project in its early growth phase.

- **Peak-day total site PV:** 75 page views (observed in the past week; monthly total ≈ 1,483 PV)
- **`/app` page peak-day visits (API-relevant):** approximately 4–8 visits
- **Unique visitors today:** approximately 10 (analytics dashboard)
- **Growth driver:** SEO-focused blog content (6 articles published to date)
- **Short-term outlook:** No significant traffic spike is anticipated in the near term

**Key point:** The blog articles, which account for the majority of site traffic, make **no YouTube API calls whatsoever**. Only users who actively use the `/app` search tool consume API quota.

The default quota limits (100 `search.list` calls/day and 10,000 units/day for the shared pool) are **more than sufficient** for current and near-term projected usage.

---

**4. Growth Plans and Factors Driving Quota Requests**

At this time, **no quota increase is being requested**. The default quota allocation comfortably covers current usage and projected growth in the foreseeable future.

Growth is being pursued gradually through organic SEO. The blog content strategy drives the majority of site traffic, but this traffic does not translate into API usage — only users who navigate to the `/app` page and perform searches consume quota. Should the `/app` user base grow significantly in the future, a separate quota increase request will be submitted at that time with updated usage data.

---

Thank you for your time and consideration. Please let me know if any additional information is needed.

Best regards,
Takeshi Kinoshita
VidScope – Project 484828457875
