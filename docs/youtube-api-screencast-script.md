# YouTube API Compliance Review — Screencast Script (English)

## Purpose
This screencast is for the YouTube API Services Compliance Review team, to clarify:
> "whether the video plays directly within the API client or if the user is redirected to the YouTube platform."

**Answer confirmed by code inspection:** VidScope embeds videos using the **official YouTube IFrame embed player** (`https://www.youtube.com/embed/{videoId}`) directly inside the app in a modal. The app also provides an optional "Open on YouTube" button/link that opens the video on youtube.com in a new tab — this is a standard, compliant pattern (same as embedding a YouTube video on any blog).

## Recording checklist (before you record)
- Screen recording tool: QuickTime (Cmd+Shift+5) on Mac, or any screen recorder.
- Record in **1280x720 or higher**, browser window maximized, no other tabs/private info visible.
- Turn off notifications.
- Have this narration ready — you can read it aloud in English, or record silently and add captions/voiceover afterward. English narration is required per YouTube's request.
- Target length: 60-90 seconds. Keep it simple and direct.

## Step-by-step actions + narration

1. **Open VidScope** (https://vidscope.app)
   > "This is VidScope, a web application that lets users search YouTube videos by keyword and see view counts and estimated revenue."

2. **Perform a search** (type a keyword, e.g. "guitar tutorial", press search)
   > "I'll search for a keyword. VidScope calls the YouTube Data API v3 search endpoint to retrieve matching videos."

3. **Show the results grid** (thumbnails, titles, view counts)
   > "Here are the search results — thumbnails, titles, and metadata returned by the YouTube Data API, displayed directly in our results grid."

4. **Click a video thumbnail to open the preview modal**
   > "When I click a video, it opens in a modal within our own application."

5. **Show the video actually playing inside the modal (embedded YouTube player)**
   > "As you can see, the video plays directly inside VidScope using YouTube's official embedded IFrame player — this is the same embed technology used across the web, for example youtube.com/embed. The user does not leave our site to watch the video."

6. **Point to / click the "Open on YouTube" button**
   > "We also provide an optional 'Open on YouTube' link, so users can choose to view the video directly on YouTube.com if they prefer — for example to like, comment, or subscribe."

7. **Close the modal, end recording.**
   > "That concludes the demonstration of how YouTube API Services are used within VidScope: search results are displayed via the Data API, and video playback happens through YouTube's official embedded player inside our application, with an optional direct link to YouTube.com."

## After recording
- Upload the video (e.g. to Google Drive or YouTube unlisted) and get a shareable link.
- Reply to YouTube's compliance email with the link (see draft reply below).
