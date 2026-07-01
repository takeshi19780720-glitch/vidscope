"""
Generate a screencast-style PDF report for YouTube API Services compliance review.
Each page shows a screenshot from the app + an English description.
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, Image, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.utils import ImageReader

SCREENSHOTS_DIR = "/Users/takeshikinoshita/Documents/Verdent/compliance/screenshots"
OUTPUT_PATH = "/Users/takeshikinoshita/Documents/Verdent/compliance/screencast_report.pdf"

# Color palette
RED_YT   = colors.HexColor("#FF0000")
DARK     = colors.HexColor("#212121")
MEDIUM   = colors.HexColor("#555555")
LIGHT_BG = colors.HexColor("#F8F8F8")
BLUE     = colors.HexColor("#1565C0")
GREEN    = colors.HexColor("#2E7D32")
AMBER    = colors.HexColor("#F57F17")
TEAL     = colors.HexColor("#00695C")
HEADER_BG = colors.HexColor("#CC0000")
BORDER   = colors.HexColor("#DDDDDD")
CAPTION_BG = colors.HexColor("#FFF0F0")
STEP_COLORS = [BLUE, GREEN, TEAL, AMBER, colors.HexColor("#6A1B9A"),
               colors.HexColor("#00838F"), colors.HexColor("#AD1457")]


def build_styles():
    base = getSampleStyleSheet()

    def add(name, **kw):
        if name not in base:
            base.add(ParagraphStyle(name=name, **kw))
        return base[name]

    add("CoverTitle",
        fontSize=26, leading=32, fontName="Helvetica-Bold",
        textColor=colors.white, alignment=TA_CENTER, spaceAfter=6)
    add("CoverSub",
        fontSize=13, leading=17, fontName="Helvetica",
        textColor=colors.HexColor("#FFCCCC"), alignment=TA_CENTER, spaceAfter=4)
    add("CoverMeta",
        fontSize=10, leading=14, fontName="Helvetica",
        textColor=colors.HexColor("#FFEEEE"), alignment=TA_CENTER)

    add("H1",
        fontSize=15, leading=19, fontName="Helvetica-Bold",
        textColor=HEADER_BG, spaceBefore=10, spaceAfter=5)
    add("StepNum",
        fontSize=20, leading=24, fontName="Helvetica-Bold",
        textColor=colors.white, alignment=TA_CENTER)
    add("StepTitle",
        fontSize=13, leading=17, fontName="Helvetica-Bold",
        textColor=colors.white)
    add("Body",
        fontSize=10, leading=15, fontName="Helvetica",
        textColor=DARK, alignment=TA_JUSTIFY, spaceAfter=4)
    add("BodySmall",
        fontSize=9, leading=13, fontName="Helvetica",
        textColor=MEDIUM, spaceAfter=3)
    add("BulletItem",
        fontSize=9.5, leading=13, fontName="Helvetica",
        textColor=DARK, leftIndent=12, spaceAfter=2)
    add("Caption",
        fontSize=8, leading=11, fontName="Helvetica-Oblique",
        textColor=MEDIUM, alignment=TA_CENTER, spaceAfter=2)
    add("Code",
        fontSize=8, leading=11, fontName="Courier",
        textColor=DARK, backColor=colors.HexColor("#F5F5F5"))
    add("Footer",
        fontSize=7.5, leading=10, fontName="Helvetica",
        textColor=colors.HexColor("#999999"), alignment=TA_CENTER)
    add("SummaryTitle",
        fontSize=11, leading=14, fontName="Helvetica-Bold",
        textColor=DARK, spaceBefore=6, spaceAfter=3)

    return base


def screenshot_image(filename, max_width=16*cm):
    """Load a screenshot and return a ReportLab Image scaled to fit."""
    path = os.path.join(SCREENSHOTS_DIR, filename)
    if not os.path.exists(path):
        return None
    try:
        reader = ImageReader(path)
        iw, ih = reader.getSize()
        ratio = ih / iw
        width = min(max_width, 16*cm)
        height = width * ratio
        # Cap height to keep on page
        if height > 12*cm:
            height = 12*cm
            width = height / ratio
        return Image(path, width=width, height=height)
    except Exception as e:
        print(f"  Warning: could not load {filename}: {e}")
        return None


def step_header(step_num, title, color, styles):
    """Build a colored step header block."""
    num_data = [[Paragraph(str(step_num), styles["StepNum"])]]
    num_t = Table(num_data, colWidths=[1.5*cm])
    num_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), color),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    title_data = [[Paragraph(title, styles["StepTitle"])]]
    title_t = Table(title_data, colWidths=[14.5*cm])
    title_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), color),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    row = Table([[num_t, title_t]], colWidths=[1.5*cm, 14.5*cm])
    row.setStyle(TableStyle([
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return row


def description_box(text, color, styles):
    """A styled description box with left accent bar."""
    data = [[Paragraph(text, styles["Body"])]]
    t = Table(data, colWidths=[16*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), LIGHT_BG),
        ("LINEBEFORE",    (0, 0), (0, -1), 3, color),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("BOX",           (0, 0), (-1, -1), 0.5, BORDER),
    ]))
    return t


def add_page_numbers(canvas_obj, doc):
    canvas_obj.saveState()
    page_num = canvas_obj.getPageNumber()
    if page_num > 1:
        canvas_obj.setFont("Helvetica", 7.5)
        canvas_obj.setFillColor(colors.HexColor("#999999"))
        canvas_obj.drawString(2.5*cm, 1.2*cm,
                              "Verdent — YouTube API Services Compliance: Step-by-Step Demonstration")
        canvas_obj.drawRightString(A4[0] - 2.5*cm, 1.2*cm, f"Page {page_num}")
        canvas_obj.setStrokeColor(BORDER)
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(2.5*cm, 1.5*cm, A4[0] - 2.5*cm, 1.5*cm)
    canvas_obj.restoreState()


def build_story(styles):
    story = []
    S = styles

    # ══════════════════════════════════════════════════════════════════════════
    # COVER PAGE
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 2.5*cm))

    cover_data = [[Paragraph("VERDENT", S["CoverTitle"])]]
    cover_t = Table(cover_data, colWidths=[16*cm])
    cover_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), HEADER_BG),
        ("TOPPADDING",    (0, 0), (-1, -1), 22),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 16),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
    ]))
    story.append(cover_t)

    sub_data = [[Paragraph("YouTube API Services Compliance", S["CoverSub"])]]
    sub_t = Table(sub_data, colWidths=[16*cm])
    sub_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#B71C1C")),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(sub_t)

    sub2_data = [[Paragraph("Step-by-Step Demonstration", S["CoverSub"])]]
    sub2_t = Table(sub2_data, colWidths=[16*cm])
    sub2_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#8B0000")),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
    ]))
    story.append(sub2_t)

    story.append(Spacer(1, 1.2*cm))

    meta_rows = [
        ["Application Name:", "Verdent — YouTube Video Search & Analysis Tool"],
        ["API Product:",       "YouTube Data API v3"],
        ["Demonstration:",     "Live application screenshots with step-by-step annotations"],
        ["Report Date:",       "June 2026"],
        ["Contact:",          "developer@verdent.app"],
    ]
    meta_t = Table(meta_rows, colWidths=[5*cm, 11*cm])
    meta_t.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",      (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 0), (-1, -1), 10),
        ("LEADING",       (0, 0), (-1, -1), 15),
        ("TEXTCOLOR",     (0, 0), (0, -1), MEDIUM),
        ("TEXTCOLOR",     (1, 0), (1, -1), DARK),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [colors.white, LIGHT_BG]),
        ("BOX",           (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, BORDER),
    ]))
    story.append(meta_t)

    story.append(Spacer(1, 1.5*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=RED_YT))
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph(
        "This report presents a live, step-by-step demonstration of the Verdent application, "
        "showing how it accesses and displays data from the YouTube Data API v3 in accordance "
        "with YouTube API Services Terms of Service and Developer Policies. "
        "Each page contains an actual screenshot from the running application, "
        "accompanied by an English description of the functionality demonstrated.",
        S["Body"]))

    story.append(Spacer(1, 0.5*cm))

    # TOC overview
    toc_rows = [
        ["Step", "Description", "Screenshot File"],
        ["1", "Application Homepage — Search Interface", "step1_homepage.png"],
        ["2", "Keyword Input — Entering 'gaming'", "step2_search_input.png"],
        ["3", "TOP 10 Results — YouTube search.list Response", "step3_top10_results.png"],
        ["4", "Trend Analysis — Statistical Graphs", "step4_trend_analysis.png"],
        ["5", "Video Cards — Detailed Result Display", "step5_card_results.png"],
        ["6", "List View — Tabular Data Comparison", "step6_list_results.png"],
        ["7", "API Quota — Real-Time Usage Monitoring", "step7_api_quota.png"],
        ["—", "Summary — API Endpoints & Compliance Notes", "(text)"],
    ]
    toc_t = Table(toc_rows, colWidths=[1.2*cm, 9.3*cm, 5.5*cm])
    toc_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("LEADING",       (0, 0), (-1, -1), 13),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("GRID",          (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("ALIGN",         (0, 0), (0, -1), "CENTER"),
    ]))
    story.append(toc_t)

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # STEP PAGES
    # ══════════════════════════════════════════════════════════════════════════
    steps = [
        {
            "num": 1,
            "title": "Application Homepage — Search Interface",
            "file": "step1_homepage.png",
            "description": (
                "The application loads at <b>http://localhost:8000/</b> and presents a clean search interface "
                "built with HTML, CSS, and vanilla JavaScript. The page includes a keyword input field, "
                "a result count selector, a search button, and a series of filter controls: "
                "video duration (all / short / normal), publication date range, content category, "
                "engagement rate, minimum view count, language, and region. "
                "A quota usage widget in the top-right corner displays real-time API quota consumption "
                "against the daily limit of 10,000 units. "
                "No YouTube API call is made until the user explicitly clicks the Search button, "
                "ensuring zero idle quota usage."
            ),
            "bullets": [
                "Front-end: static HTML/CSS/JS served by FastAPI's StaticFiles middleware.",
                "Back-end: FastAPI (Python) running on uvicorn at port 8000.",
                "No user authentication is required; the app uses a server-side API key.",
                "All YouTube data is fetched server-side; the API key is never exposed to the browser.",
            ],
        },
        {
            "num": 2,
            "title": "Keyword Input — Entering 'gaming'",
            "file": "step2_search_input.png",
            "description": (
                "The user types the keyword <b>'gaming'</b> into the search input field. "
                "At this stage, no API request has been sent yet — the application waits for the "
                "user to click the Search button. "
                "The search form allows users to specify a keyword, maximum number of results (1–200), "
                "and optional filters. A comparison mode (side-by-side keyword analysis) is also "
                "available via the 'Compare' button. "
                "Keyword search history is stored locally in the browser's localStorage only, "
                "and is never transmitted to the server or any third party."
            ),
            "bullets": [
                "Keyword: 'gaming' (entered by the user).",
                "Optional filters: duration, date range, category, engagement, views, language, region.",
                "No API call is triggered until the Search button is clicked.",
                "Search history is stored only in browser localStorage — not on the server.",
            ],
        },
        {
            "num": 3,
            "title": "TOP 10 Results — YouTube search.list Response",
            "file": "step3_top10_results.png",
            "description": (
                "After the user clicks Search, the application calls the back-end <b>/api/search</b> endpoint. "
                "The back-end issues a <b>search.list</b> request to the YouTube Data API v3 "
                "(consuming 100 quota units) to retrieve video IDs and snippet metadata. "
                "It then batches the IDs and calls <b>videos.list</b> (1 quota unit per batch of up to 50) "
                "to fetch full statistics, and <b>channels.list</b> (1 unit per batch) for subscriber counts. "
                "The top 10 videos by view count are displayed in a prominently styled 'TOP 10' section. "
                "Each entry shows: video rank, thumbnail, title, channel name, subscriber count, "
                "view count, like count, duration, estimated revenue, and engagement rate."
            ),
            "bullets": [
                "API call 1: search.list — part=snippet, type=video, maxResults=50, order=viewCount (100 quota units).",
                "API call 2: videos.list — part=statistics,snippet,contentDetails (1 unit per batch).",
                "API call 3: channels.list — part=statistics,snippet (1 unit per batch).",
                "Results are sorted by view count (descending) server-side.",
                "Results cached in-memory for 30 minutes (CACHE_TTL = 1800 s).",
            ],
        },
        {
            "num": 4,
            "title": "Trend Analysis — Statistical Graphs (Horizontal Bar Charts)",
            "file": "step4_trend_analysis.png",
            "description": (
                "Below the TOP 10 section, Verdent renders a suite of statistical charts "
                "derived exclusively from the YouTube Data API response. "
                "All graphs use horizontal bar chart layout (Chart.js <b>indexAxis: 'y'</b>), "
                "making category labels easy to read. "
                "Charts displayed include: country-wise video count, country-wise total views, "
                "view count distribution, engagement rate distribution, category-wise video count, "
                "category-wise total views, category-wise estimated revenue, top-10 tags, "
                "top-10 title keywords, day-of-week posting distribution, hourly posting distribution, "
                "and video duration vs. view count correlation. "
                "All chart data is computed client-side from the API response — no additional API calls "
                "are made to render the analytics."
            ),
            "bullets": [
                "All charts use Chart.js v4 rendered on <canvas> elements.",
                "Data source: API fields returned by search.list, videos.list, channels.list.",
                "No additional API calls are triggered to render the trend analysis section.",
                "Individual charts can be shown/hidden; graph color is user-configurable.",
            ],
        },
        {
            "num": 5,
            "title": "Video Cards — Detailed Result Display",
            "file": "step5_card_results.png",
            "description": (
                "The full search results list is displayed below the trend analysis section "
                "in a responsive card layout. Each video card shows: "
                "the video thumbnail (hotlinked from i.ytimg.com as provided by the API), "
                "the video title (clickable, opens a preview modal), "
                "the channel name (clickable, opens channel details modal), "
                "subscriber count, total view count, like count, video duration, "
                "publication date (displayed as relative age, e.g. '3 days ago'), "
                "content category, engagement rate (%), and estimated revenue (JPY). "
                "Each card also features a direct 'Open on YouTube' link and a Favourite button. "
                "Engagement Rate is calculated as <i>likeCount / viewCount × 100</i>. "
                "Estimated Revenue uses a per-genre CPM (configurable by the user in Settings) "
                "multiplied by viewCount / 1000."
            ),
            "bullets": [
                "Thumbnail: served from i.ytimg.com (YouTube CDN) — URL from snippet.thumbnails.",
                "Title / channel name: from snippet.title / snippet.channelTitle.",
                "View / like / comment counts: from statistics.*.",
                "Duration: parsed from contentDetails.duration (ISO 8601).",
                "Engagement Rate & Estimated Revenue: derived metrics, clearly labelled.",
                "Each card links back to https://www.youtube.com/watch?v=<videoId>.",
            ],
        },
        {
            "num": 6,
            "title": "List View — Tabular Data Comparison",
            "file": "step6_list_results.png",
            "description": (
                "By clicking the list-view toggle button (the three-line icon next to the card-view icon), "
                "the user switches from the card layout to a compact tabular view. "
                "The table presents the same data fields as the card view — title, channel, subscribers, "
                "views, likes, duration, engagement rate, estimated revenue, and publication date — "
                "in a horizontally scrollable table. "
                "This view is particularly useful for quickly comparing multiple videos side-by-side "
                "without scrolling through individual cards. "
                "Switching view modes does not trigger any new API calls; "
                "the data is already in memory from the initial search."
            ),
            "bullets": [
                "Toggle button: #view-list-btn (SVG icon, no text label).",
                "Table is horizontally scrollable on narrow viewports.",
                "No additional API calls are made when switching view modes.",
                "CSV and Excel export buttons are available above the table.",
            ],
        },
        {
            "num": 7,
            "title": "API Quota — Real-Time Usage Monitoring",
            "file": "step7_api_quota.png",
            "description": (
                "The <b>/api/quota</b> endpoint returns a JSON object showing the current "
                "API quota consumption tracked by the application. "
                "The response includes the number of quota units used so far in the current day, "
                "the daily quota limit (10,000 units by default), the number of remaining units, "
                "and a breakdown of calls made by endpoint type. "
                "This endpoint is also consumed by the quota widget in the UI header, "
                "which updates automatically after each search. "
                "If the remaining quota falls below 20% of the daily limit, "
                "the application displays a warning banner and rate-limits new requests. "
                "The quota counter is stored in-memory and resets at midnight UTC."
            ),
            "bullets": [
                "Endpoint: GET /api/quota — returns JSON (no authentication required).",
                "Quota tracking: in-memory counter, incremented by youtube_client.py after each API call.",
                "Daily limit: 10,000 units (standard YouTube Data API v3 default quota).",
                "search.list: 100 units per call; videos.list / channels.list: 1 unit per batch.",
                "Counter resets at server restart (stateless, no persistent storage of quota data).",
            ],
        },
    ]

    for step in steps:
        color = STEP_COLORS[(step["num"] - 1) % len(STEP_COLORS)]

        # Step header
        story.append(step_header(step["num"], step["title"], color, S))
        story.append(Spacer(1, 0.4*cm))

        # Screenshot
        img = screenshot_image(step["file"])
        if img:
            # Center the image
            img_data = [[img]]
            img_t = Table(img_data, colWidths=[16*cm])
            img_t.setStyle(TableStyle([
                ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
                ("BOX",           (0, 0), (-1, -1), 0.5, BORDER),
                ("TOPPADDING",    (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(img_t)
            story.append(Paragraph(
                f"Screenshot: {step['file']}  |  Browser viewport: 1280 × 800 px  |  "
                "Captured with Playwright (headless Chromium)",
                S["Caption"]))
        else:
            missing_data = [[Paragraph(
                f"[Screenshot not available: {step['file']}]", S["BodySmall"])]]
            missing_t = Table(missing_data, colWidths=[16*cm])
            missing_t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF9C4")),
                ("BOX",        (0, 0), (-1, -1), 0.5, AMBER),
                ("LEFTPADDING",(0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
            ]))
            story.append(missing_t)

        story.append(Spacer(1, 0.3*cm))

        # Description
        story.append(description_box(step["description"], color, S))
        story.append(Spacer(1, 0.2*cm))

        # Bullet points
        for bullet in step["bullets"]:
            story.append(Paragraph(f"&bull; &nbsp; {bullet}", S["BulletItem"]))

        story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # SUMMARY PAGE
    # ══════════════════════════════════════════════════════════════════════════
    # Section header
    summary_header_data = [[Paragraph("Summary — API Usage &amp; Compliance", S["H1"])]]
    summary_header_t = Table(summary_header_data, colWidths=[16*cm])
    summary_header_t.setStyle(TableStyle([
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("LINEBEFORE",   (0, 0), (0, -1), 3, RED_YT),
        ("BACKGROUND",   (0, 0), (-1, -1), colors.HexColor("#FFF0F0")),
    ]))
    story.append(summary_header_t)
    story.append(Spacer(1, 0.4*cm))

    # API Endpoints table
    story.append(Paragraph("<b>YouTube Data API v3 Endpoints Used</b>", S["SummaryTitle"]))
    endpoint_rows = [
        ["Endpoint", "Parameters", "Quota Cost", "Purpose"],
        ["search.list",
         "part=snippet, type=video, q=<keyword>, maxResults=50, order=viewCount",
         "100 units/call",
         "Retrieve video IDs and snippet metadata for the keyword query."],
        ["videos.list",
         "part=statistics,snippet,contentDetails, id=<comma-separated IDs>",
         "1 unit/batch (up to 50 IDs)",
         "Fetch view count, like count, comment count, duration, and category for each video."],
        ["channels.list",
         "part=statistics,snippet, id=<comma-separated channel IDs>",
         "1 unit/batch (up to 50 IDs)",
         "Fetch subscriber count, channel thumbnail, and uploads playlist ID."],
    ]
    ep_t = Table(endpoint_rows, colWidths=[3.5*cm, 6.5*cm, 2.5*cm, 3.5*cm])
    ep_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8.5),
        ("LEADING",       (0, 0), (-1, -1), 12),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("GRID",          (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(ep_t)
    story.append(Spacer(1, 0.4*cm))

    # Caching strategy
    story.append(Paragraph("<b>Caching Strategy (30-Minute In-Memory TTL)</b>", S["SummaryTitle"]))
    story.append(Paragraph(
        "Verdent implements a server-side in-memory cache keyed by a MD5 hash of the "
        "search parameters (keyword + max_results + duration_filter + published_after + "
        "category_id + language + region). "
        "Cache entries expire after <b>1,800 seconds (30 minutes)</b>. "
        "If an identical search is repeated within this window, the cached response is "
        "returned immediately with zero additional API calls. "
        "The cache holds a maximum of 100 entries; expired entries are purged automatically. "
        "A separate channel-info cache (maximum 200 entries, same 30-minute TTL) stores "
        "channel metadata fetched via channels.list.",
        S["Body"]))
    story.append(Spacer(1, 0.3*cm))

    # Quota optimisation
    story.append(Paragraph("<b>Quota Optimisation</b>", S["SummaryTitle"]))
    opt_rows = [
        ["Technique", "Detail", "Quota Saving"],
        ["In-Memory Cache (30 min TTL)",
         "Identical searches served from cache — no API call made.",
         "Saves 100+ units per repeated query"],
        ["Batch API Requests",
         "Up to 50 video IDs or channel IDs per request to videos.list / channels.list.",
         "1 unit per 50 items vs. 50 units individually"],
        ["On-Demand Only",
         "No background polling, auto-refresh, or prefetching.",
         "Zero idle quota consumption"],
        ["API Key Rotation",
         "Multiple API keys supported; automatic rotation on 403/quota-exceeded responses.",
         "Prevents service interruption at quota limit"],
    ]
    opt_t = Table(opt_rows, colWidths=[4.2*cm, 8.3*cm, 3.5*cm])
    opt_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8.5),
        ("LEADING",       (0, 0), (-1, -1), 12),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("GRID",          (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(opt_t)
    story.append(Spacer(1, 0.4*cm))

    # Compliance summary
    story.append(Paragraph("<b>Compliance Confirmation</b>", S["SummaryTitle"]))
    compliance_items = [
        "<b>Read-Only Access:</b> All API calls use GET requests only. No YouTube resources are created, updated, or deleted.",
        "<b>Official API Only:</b> All data is retrieved exclusively via the YouTube Data API v3 REST endpoints. No scraping or unofficial interfaces.",
        "<b>No Unauthorised Redistribution:</b> API data is displayed only within the Verdent application interface and is never sold or redistributed.",
        "<b>Attribution:</b> All video and channel data is attributed to YouTube/Google in the application UI footer.",
        "<b>Quota Compliance:</b> Daily quota is monitored via /api/quota. The app warns users when usage exceeds 80% and respects the 10,000-unit daily limit.",
        "<b>No Personal Data:</b> No OAuth authentication is performed. No user viewing history, subscriptions, or personally identifiable information is accessed.",
        "<b>Data Retention:</b> API responses are cached in-memory for a maximum of 30 minutes and are never written to persistent storage.",
        "<b>YouTube Attribution:</b> Every video card provides a direct link to the original video on YouTube.com.",
    ]
    for item in compliance_items:
        story.append(Paragraph(f"&bull; &nbsp; {item}", S["BulletItem"]))

    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "This report was generated programmatically using the Verdent compliance reporting system. "
        "Screenshots were captured from the live application using Playwright (headless Chromium, "
        "viewport 1280×800). For questions, contact developer@verdent.app.",
        S["Footer"]))

    return story


def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=A4,
        topMargin=2.0*cm,
        bottomMargin=2.2*cm,
        leftMargin=2.5*cm,
        rightMargin=2.5*cm,
        title="Verdent — YouTube API Services Compliance: Step-by-Step Demonstration",
        author="Verdent Development Team",
        subject="YouTube API Services Compliance Review",
    )
    styles = build_styles()
    story = build_story(styles)
    doc.build(story, onFirstPage=add_page_numbers, onLaterPages=add_page_numbers)
    size_kb = os.path.getsize(OUTPUT_PATH) // 1024
    print(f"PDF generated: {OUTPUT_PATH}  ({size_kb} KB)")


if __name__ == "__main__":
    main()
