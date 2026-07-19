# Draft reply to YouTube API Services Compliance Review

Subject: Re: YouTube API Services Compliance Review — Follow-up

Hello,

Thank you for the follow-up. To clarify, in VidScope (https://vidscope.app), video playback happens **directly within our application**, using YouTube's official embedded IFrame Player API (the standard `https://www.youtube.com/embed/{videoId}` embed). Users are not redirected away from our site to watch a video.

We also provide an optional "Open on YouTube" link/button next to each video, which users can click if they wish to view the video directly on YouTube.com (e.g. to like, comment, or subscribe to the channel).

Please find attached/linked a screen recording demonstrating this end-to-end flow:
1. Searching for videos via the YouTube Data API
2. Viewing search results with metadata
3. Clicking a video and watching it play in-app via the embedded YouTube player
4. The optional "Open on YouTube" link

Screencast link: https://drive.google.com/file/d/1wV_rZMALPTA-yyuYVhjusmn2L_YlX31j/view?usp=drive_link

Please let us know if any additional information is needed.

Thank you,
Takeshi Kinoshita
VidScope
