"""
Generate YouTube API Services compliance sample report PDF.
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

OUTPUT_PATH = "/Users/takeshikinoshita/Documents/Verdent/compliance/sample_report.pdf"

# ── Color palette ──────────────────────────────────────────────────────────────
RED_YT   = colors.HexColor("#FF0000")
DARK     = colors.HexColor("#212121")
MEDIUM   = colors.HexColor("#555555")
LIGHT_BG = colors.HexColor("#F8F8F8")
BLUE     = colors.HexColor("#1565C0")
GREEN    = colors.HexColor("#2E7D32")
AMBER    = colors.HexColor("#F57F17")
TEAL     = colors.HexColor("#00695C")
HEADER_BG = colors.HexColor("#CC0000")
ROW_ALT  = colors.HexColor("#FFF5F5")
CODE_BG  = colors.HexColor("#F5F5F5")
BORDER   = colors.HexColor("#DDDDDD")

def build_styles():
    base = getSampleStyleSheet()

    def add(name, **kw):
        if name not in base:
            base.add(ParagraphStyle(name=name, **kw))
        return base[name]

    add("CoverTitle",
        fontSize=28, leading=34, fontName="Helvetica-Bold",
        textColor=colors.white, alignment=TA_CENTER, spaceAfter=6)
    add("CoverSub",
        fontSize=14, leading=18, fontName="Helvetica",
        textColor=colors.HexColor("#FFCCCC"), alignment=TA_CENTER, spaceAfter=4)
    add("CoverMeta",
        fontSize=10, leading=14, fontName="Helvetica",
        textColor=colors.HexColor("#FFEEEE"), alignment=TA_CENTER)

    add("H1",
        fontSize=16, leading=20, fontName="Helvetica-Bold",
        textColor=HEADER_BG, spaceBefore=14, spaceAfter=6)
    add("H2",
        fontSize=13, leading=17, fontName="Helvetica-Bold",
        textColor=DARK, spaceBefore=10, spaceAfter=4)
    add("H3",
        fontSize=11, leading=15, fontName="Helvetica-Bold",
        textColor=MEDIUM, spaceBefore=6, spaceAfter=3)

    add("Body",
        fontSize=10, leading=15, fontName="Helvetica",
        textColor=DARK, alignment=TA_JUSTIFY, spaceAfter=4)
    add("BodySmall",
        fontSize=9, leading=13, fontName="Helvetica",
        textColor=MEDIUM, spaceAfter=3)
    add("Code",
        fontSize=8.5, leading=12, fontName="Courier",
        textColor=DARK, backColor=CODE_BG, spaceAfter=2,
        leftIndent=8, rightIndent=8)
    add("BulletItem",
        fontSize=10, leading=14, fontName="Helvetica",
        textColor=DARK, leftIndent=14, spaceAfter=2)
    add("StepLabel",
        fontSize=11, leading=14, fontName="Helvetica-Bold",
        textColor=colors.white)
    add("StepBody",
        fontSize=10, leading=14, fontName="Helvetica",
        textColor=DARK, leftIndent=10, spaceAfter=3)
    add("Caption",
        fontSize=8, leading=11, fontName="Helvetica-Oblique",
        textColor=MEDIUM, alignment=TA_CENTER, spaceAfter=2)
    add("Note",
        fontSize=9, leading=13, fontName="Helvetica",
        textColor=colors.HexColor("#5D4037"),
        backColor=colors.HexColor("#FFF8E1"),
        leftIndent=6, rightIndent=6, spaceBefore=2, spaceAfter=4)
    add("Legal",
        fontSize=9, leading=13, fontName="Helvetica",
        textColor=MEDIUM, alignment=TA_JUSTIFY, spaceAfter=3)
    add("Footer",
        fontSize=7.5, leading=10, fontName="Helvetica",
        textColor=colors.HexColor("#999999"), alignment=TA_CENTER)

    return base


def section_header(text, styles):
    """Returns a red left-border section title block."""
    data = [[Paragraph(text, styles["H1"])]]
    t = Table(data, colWidths=[16*cm])
    t.setStyle(TableStyle([
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("LINEBEFORE",   (0, 0), (0, -1), 3, RED_YT),
        ("BACKGROUND",   (0, 0), (-1, -1), colors.HexColor("#FFF0F0")),
    ]))
    return t


def code_block(lines, styles):
    """Returns a styled code-like table block."""
    text = "<br/>".join(lines)
    data = [[Paragraph(text, styles["Code"])]]
    t = Table(data, colWidths=[16*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), CODE_BG),
        ("BOX",          (0, 0), (-1, -1), 0.5, BORDER),
        ("LEFTPADDING",  (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING",   (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
    ]))
    return t


def info_box(text, color, styles, bg=None):
    """Colored info / note box."""
    if bg is None:
        bg = colors.HexColor("#E3F2FD")
    data = [[Paragraph(text, styles["Note"])]]
    t = Table(data, colWidths=[16*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), bg),
        ("LINEBEFORE",   (0, 0), (0, -1), 3, color),
        ("LEFTPADDING",  (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
    ]))
    return t


def build_story(styles):
    story = []
    S = styles

    # ══════════════════════════════════════════════════════════════════════════
    # COVER PAGE
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 2.5*cm))

    # Red banner
    cover_data = [[
        Paragraph("YOUTUBE API SERVICES", S["CoverTitle"]),
    ]]
    cover_t = Table(cover_data, colWidths=[16*cm])
    cover_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), HEADER_BG),
        ("TOPPADDING",    (0, 0), (-1, -1), 20),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 16),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
    ]))
    story.append(cover_t)

    sub_data = [[
        Paragraph("Compliance Verification Report", S["CoverSub"]),
    ]]
    sub_t = Table(sub_data, colWidths=[16*cm])
    sub_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#B71C1C")),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ("LEFTPADDING",   (0, 0), (-1, -1), 16),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
    ]))
    story.append(sub_t)

    story.append(Spacer(1, 1.2*cm))

    meta_rows = [
        ["Application Name:", "Verdent"],
        ["Application URL:", "https://verdent.app"],
        ["API Product:",      "YouTube Data API v3"],
        ["Report Version:",   "1.0"],
        ["Prepared Date:",    "June 2026"],
        ["Contact:",         "developer@verdent.app"],
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
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [colors.white, LIGHT_BG]),
        ("BOX",           (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, BORDER),
    ]))
    story.append(meta_t)

    story.append(Spacer(1, 1.5*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=RED_YT))
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph(
        "This document is prepared for submission to Google as part of the "
        "YouTube API Services compliance review process. It demonstrates how "
        "Verdent fetches, processes, and displays data obtained through the "
        "YouTube Data API v3, and confirms adherence to all applicable "
        "YouTube API Services Terms of Service.",
        S["Body"]))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1 — APPLICATION OVERVIEW
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_header("1. Application Overview", S))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>Application Name:</b> Verdent", S["Body"]))
    story.append(Paragraph("<b>Application URL:</b> https://verdent.app", S["Body"]))
    story.append(Paragraph("<b>Platform:</b> Web application (macOS desktop client also available)", S["Body"]))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph(
        "Verdent is a YouTube channel analytics and keyword research tool designed for "
        "individual content creators, digital marketers, and media researchers. "
        "The application enables users to search for YouTube videos by keyword, "
        "analyze video performance metrics, compare channel growth, and estimate "
        "revenue potential based on publicly available engagement data.",
        S["Body"]))

    story.append(Paragraph(
        "The application does not allow end-users to upload, modify, or delete "
        "YouTube content. All interactions with the YouTube Data API v3 are "
        "strictly read-only. No user authentication via OAuth is performed; "
        "the application uses an API key scoped exclusively to read access.",
        S["Body"]))

    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("<b>Purpose of YouTube API Usage</b>", S["H2"]))
    purpose_items = [
        "Retrieve video search results based on user-supplied keywords (search.list).",
        "Fetch detailed video statistics such as view count, like count, and comment count (videos.list).",
        "Retrieve channel-level information including subscriber count and channel description (channels.list).",
        "Obtain the mapping of video category IDs to human-readable category names (videoCategories.list).",
    ]
    for item in purpose_items:
        story.append(Paragraph(f"&bull; &nbsp; {item}", S["BulletItem"]))

    story.append(Spacer(1, 0.3*cm))
    story.append(info_box(
        "<b>Data Use Limitation:</b> All data retrieved from the YouTube Data API v3 is "
        "used solely to display analytics information within the Verdent application. "
        "No data is sold, redistributed, or used for advertising purposes.",
        BLUE, S, bg=colors.HexColor("#E8F4FD")))

    story.append(Spacer(1, 0.4*cm))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2 — API USAGE FLOW
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_header("2. API Usage Flow", S))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph(
        "The following steps describe the complete data-retrieval flow triggered "
        "when a user performs a keyword search in Verdent. Each step maps to one "
        "or more YouTube Data API v3 endpoints.",
        S["Body"]))
    story.append(Spacer(1, 0.3*cm))

    steps = [
        ("Step 1", "User Enters a Keyword  →  search.list",
         "The user types a keyword (e.g., \"AI tutorial\") and optionally selects a "
         "date-range filter (past 24 h, past week, past month, or custom). "
         "Verdent calls <b>search.list</b> with parameters: "
         "<i>part=snippet</i>, <i>type=video</i>, <i>maxResults=50</i>, "
         "and <i>publishedAfter</i>/<i>publishedBefore</i> if a date filter is active. "
         "The response returns a list of video IDs and snippet metadata "
         "(title, channel ID, thumbnail URL, publish date)."),
        ("Step 2", "Video IDs Collected  →  videos.list",
         "The video IDs returned by search.list are batched (up to 50 per request) "
         "and passed to <b>videos.list</b> with "
         "<i>part=statistics,snippet,contentDetails</i>. "
         "This retrieves viewCount, likeCount, commentCount, duration, and "
         "category ID for each video. Batching minimises quota consumption."),
        ("Step 3", "Channel IDs Collected  →  channels.list",
         "Unique channel IDs extracted from the search results are batched and sent "
         "to <b>channels.list</b> with <i>part=statistics,snippet</i>. "
         "This provides subscriberCount, videoCount, viewCount, and the channel "
         "thumbnail URL displayed alongside each result."),
        ("Step 4", "Results Displayed with Estimated Revenue",
         "All retrieved data is merged in-memory and rendered in the Verdent UI. "
         "An estimated revenue figure is derived from publicly available CPM "
         "benchmarks and the video's viewCount: "
         "<i>Estimated Revenue = CPM x viewCount / 1000</i>. "
         "This figure is labelled as an estimate and is never returned by the API."),
    ]

    step_colors = [BLUE, GREEN, TEAL, AMBER]
    for (label, title, body), clr in zip(steps, step_colors):
        label_data = [[Paragraph(f"<b>{label}</b>", S["StepLabel"])]]
        label_t = Table(label_data, colWidths=[2.4*cm])
        label_t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), clr),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ]))
        body_data = [[
            Paragraph(f"<b>{title}</b><br/>{body}", S["Body"])
        ]]
        body_t = Table(body_data, colWidths=[13.6*cm])
        body_t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), LIGHT_BG),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
            ("BOX",           (0, 0), (-1, -1), 0.5, BORDER),
        ]))
        row = Table([[label_t, body_t]], colWidths=[2.4*cm, 13.6*cm])
        row.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(KeepTogether([row, Spacer(1, 0.25*cm)]))

    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("<b>Quota Optimisation Strategy</b>", S["H2"]))
    story.append(Paragraph(
        "Verdent implements two layers of quota conservation to comply with "
        "the YouTube API Services usage policies:",
        S["Body"]))
    quota_rows = [
        ["Strategy", "Details", "Quota Saving"],
        ["Daily Search Cache",
         "Results for identical keyword + date-range combinations are cached "
         "for 24 hours in a local SQLite database.",
         "Eliminates repeat search.list calls (100 units each)"],
        ["Batch API Requests",
         "video IDs and channel IDs are grouped into batches of up to 50, "
         "reducing the number of API calls by up to 50x.",
         "1 unit per batch vs. 1 unit per item"],
        ["On-Demand Only",
         "API calls are triggered only by explicit user action; "
         "no background polling or automatic refresh.",
         "Zero idle quota usage"],
    ]
    qt = Table(quota_rows, colWidths=[3.5*cm, 8.5*cm, 4*cm])
    qt.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("LEADING",       (0, 0), (-1, -1), 13),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("GRID",          (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(qt)

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3 — SAMPLE DATA
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_header("3. Sample API Response Data", S))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph(
        "This section provides annotated excerpts of actual API responses "
        "returned by the YouTube Data API v3. Sensitive personal data "
        "(OAuth tokens, internal user IDs) is not involved because the "
        "application uses API-key-only authentication for public data.",
        S["Body"]))

    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("<b>3.1  search.list Response Excerpt</b>", S["H2"]))
    story.append(Paragraph(
        "The following is a representative JSON excerpt returned by "
        "<b>search.list</b> for the query \"AI tutorial\" with "
        "publishedAfter set to 7 days prior to the request date:",
        S["Body"]))

    json_lines = [
        '{',
        '  "kind": "youtube#searchListResponse",',
        '  "etag": "someEtagValue",',
        '  "nextPageToken": "CAUQAA",',
        '  "regionCode": "JP",',
        '  "pageInfo": { "totalResults": 1000000, "resultsPerPage": 50 },',
        '  "items": [',
        '    {',
        '      "kind": "youtube#searchResult",',
        '      "id": { "kind": "youtube#video", "videoId": "dQw4w9WgXcQ" },',
        '      "snippet": {',
        '        "publishedAt": "2026-06-14T10:30:00Z",',
        '        "channelId": "UCxxxxxxxxxxxxxxxxxxxxxx",',
        '        "title": "Complete AI Tutorial for Beginners 2026",',
        '        "description": "Learn AI from scratch ...",',
        '        "channelTitle": "TechLearn Pro",',
        '        "thumbnails": {',
        '          "medium": {',
        '            "url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/mqdefault.jpg",',
        '            "width": 320, "height": 180',
        '          }',
        '        },',
        '        "liveBroadcastContent": "none"',
        '      }',
        '    }',
        '    // ... up to 50 items per page',
        '  ]',
        '}',
    ]
    story.append(code_block(json_lines, S))
    story.append(Spacer(1, 0.2*cm))

    annotations = [
        ("<b>videoId</b>", "Used as the key for subsequent videos.list calls (batched)."),
        ("<b>channelId</b>", "Collected for a batched channels.list call."),
        ("<b>title / description</b>", "Displayed verbatim in the search results UI."),
        ("<b>thumbnails.medium.url</b>", "Displayed as a thumbnail image; the URL is not stored persistently."),
        ("<b>publishedAt</b>", "Used to calculate relative post age (e.g., '5 days ago') shown in the UI."),
    ]
    ann_rows = [["Field", "How Verdent uses it"]] + [[k, v] for k, v in annotations]
    ann_t = Table(ann_rows, colWidths=[4.5*cm, 11.5*cm])
    ann_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), TEAL),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("LEADING",       (0, 0), (-1, -1), 13),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#E0F2F1")]),
        ("GRID",          (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(ann_t)
    story.append(Spacer(1, 0.4*cm))

    story.append(Paragraph("<b>3.2  videos.list Response Excerpt</b>", S["H2"]))
    vids_lines = [
        '{',
        '  "kind": "youtube#videoListResponse",',
        '  "items": [',
        '    {',
        '      "kind": "youtube#video",',
        '      "id": "dQw4w9WgXcQ",',
        '      "snippet": { "categoryId": "28" },',
        '      "statistics": {',
        '        "viewCount":    "1523847",',
        '        "likeCount":    "48201",',
        '        "commentCount": "3912"',
        '      },',
        '      "contentDetails": { "duration": "PT14M32S" }',
        '    }',
        '  ]',
        '}',
    ]
    story.append(code_block(vids_lines, S))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>3.3  Caching Strategy</b>", S["H2"]))
    story.append(Paragraph(
        "Search results are cached in a local SQLite database using the "
        "following schema. The cache key is a SHA-256 hash of the query "
        "parameters (keyword + date range). Cache entries expire after "
        "86,400 seconds (24 hours), after which the next request triggers "
        "a fresh API call.",
        S["Body"]))
    cache_lines = [
        "CREATE TABLE search_cache (",
        "  cache_key   TEXT PRIMARY KEY,   -- SHA-256(keyword + date_range)",
        "  response    TEXT NOT NULL,       -- serialised JSON response",
        "  fetched_at  INTEGER NOT NULL,    -- Unix timestamp",
        "  expires_at  INTEGER NOT NULL     -- fetched_at + 86400",
        ");",
    ]
    story.append(code_block(cache_lines, S))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 4 — DISPLAYED CONTENT
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_header("4. Information Displayed to Users", S))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph(
        "The following table enumerates every data field originating from the "
        "YouTube Data API v3 that is rendered in the Verdent user interface, "
        "together with the API source and the display context.",
        S["Body"]))
    story.append(Spacer(1, 0.3*cm))

    display_rows = [
        ["Field", "API Source", "Display Context", "Stored?"],
        ["Video thumbnail", "search.list (snippet.thumbnails)", "Search result card", "No (URL only, in cache)"],
        ["Video title", "search.list (snippet.title)", "Search result card, detail panel", "Yes (in cache)"],
        ["Channel name", "search.list (snippet.channelTitle)", "Search result card", "Yes (in cache)"],
        ["Publish date", "search.list (snippet.publishedAt)", "Relative age label", "Yes (in cache)"],
        ["View count", "videos.list (statistics.viewCount)", "Metric card, trend chart", "Yes (in cache)"],
        ["Like count", "videos.list (statistics.likeCount)", "Engagement rate calc.", "Yes (in cache)"],
        ["Comment count", "videos.list (statistics.commentCount)", "Engagement rate calc.", "Yes (in cache)"],
        ["Video duration", "videos.list (contentDetails.duration)", "Duration badge", "Yes (in cache)"],
        ["Subscriber count", "channels.list (statistics.subscriberCount)", "Channel info panel", "Yes (in cache)"],
        ["Channel thumbnail", "channels.list (snippet.thumbnails)", "Channel info panel", "No (URL only, in cache)"],
        ["Video category", "videoCategories.list", "Category filter tag", "Yes (look-up table)"],
    ]
    dt = Table(display_rows, colWidths=[3.3*cm, 4.2*cm, 4.2*cm, 4.3*cm])
    dt.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8.5),
        ("LEADING",       (0, 0), (-1, -1), 12),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, ROW_ALT]),
        ("GRID",          (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(dt)

    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph("<b>4.1  Derived Metrics (Not Returned by the API)</b>", S["H2"]))
    story.append(Paragraph(
        "Verdent computes two derived metrics from the raw API data. "
        "These values are clearly labelled as estimates in the UI.",
        S["Body"]))

    derived_rows = [
        ["Metric", "Formula", "Label in UI"],
        ["Engagement Rate",
         "(likeCount + commentCount) / viewCount x 100",
         "Engagement Rate (%)"],
        ["Estimated Revenue",
         "CPM (user-configurable, default $2) x viewCount / 1000",
         "Est. Revenue (USD) — Estimate Only"],
    ]
    drt = Table(derived_rows, colWidths=[3.8*cm, 7.4*cm, 4.8*cm])
    drt.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("LEADING",       (0, 0), (-1, -1), 13),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("GRID",          (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(drt)

    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph("<b>4.2  Trend Analytics</b>", S["H2"]))
    story.append(Paragraph(
        "Verdent aggregates the video data retrieved for a given search to "
        "render the following trend charts. All chart data is derived "
        "exclusively from API fields listed in the table above:",
        S["Body"]))
    trends = [
        "Upload time-of-day distribution (bar chart) — derived from publishedAt.",
        "Day-of-week distribution (bar chart) — derived from publishedAt.",
        "View count distribution (histogram) — derived from statistics.viewCount.",
        "Subscriber count vs. view count scatter plot — channel-level correlation.",
        "Category breakdown (pie chart) — derived from videoCategories.list.",
    ]
    for t in trends:
        story.append(Paragraph(f"&bull; &nbsp; {t}", S["BulletItem"]))

    story.append(Spacer(1, 0.2*cm))
    story.append(info_box(
        "<b>No Personal Data:</b> None of the fields displayed or computed by Verdent "
        "constitute personal data as defined under applicable privacy regulations. "
        "Verdent does not collect, store, or process any information that could "
        "identify individual YouTube viewers.",
        GREEN, S, bg=colors.HexColor("#E8F5E9")))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 5 — TERMS OF SERVICE COMPLIANCE
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_header("5. YouTube API Services Terms of Service Compliance", S))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph(
        "Verdent has reviewed and acknowledges all provisions of the "
        "<b>YouTube API Services Terms of Service</b> "
        "(https://developers.google.com/youtube/terms/api-services-terms-of-service) "
        "and the <b>YouTube API Services Developer Policies</b>. "
        "The following sub-sections describe how the application satisfies "
        "each material requirement.",
        S["Body"]))

    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph("<b>5.1  Acceptable Use</b>", S["H2"]))

    compliance_items = [
        ("Read-Only Access",
         "All API calls use GET requests only. Verdent does not create, update, "
         "or delete YouTube resources. No OAuth scopes beyond public-data access "
         "are requested."),
        ("No Data Scraping",
         "Verdent relies solely on the YouTube Data API v3 for data retrieval. "
         "No HTML scraping, reverse-engineered endpoints, or unofficial YouTube "
         "interfaces are used."),
        ("No Unauthorised Redistribution",
         "API data is displayed only within the Verdent application interface. "
         "No bulk data export, resale, or redistribution to third parties occurs."),
        ("Attribution",
         "All video and channel data is attributed to YouTube / Google LLC in the "
         "application UI footer and in the application's About page, as required "
         "by the Branding Guidelines."),
        ("Quota Compliance",
         "The application monitors its daily quota consumption and displays a "
         "warning when usage exceeds 80% of the allocated quota. Automated "
         "back-off logic prevents quota exhaustion."),
    ]
    for title_text, body_text in compliance_items:
        row_data = [[
            Paragraph(f"<b>{title_text}</b><br/><font size='9'>{body_text}</font>",
                      S["Body"])
        ]]
        ct = Table(row_data, colWidths=[16*cm])
        ct.setStyle(TableStyle([
            ("LEFTPADDING",  (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING",   (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
            ("LINEBEFORE",   (0, 0), (0, -1), 3, GREEN),
            ("BACKGROUND",   (0, 0), (-1, -1), colors.HexColor("#F1F8E9")),
            ("BOX",          (0, 0), (-1, -1), 0.5, BORDER),
        ]))
        story.append(KeepTogether([ct, Spacer(1, 0.2*cm)]))

    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph("<b>5.2  User Privacy and Data Protection</b>", S["H2"]))
    story.append(Paragraph(
        "Verdent does not authenticate end-users via Google/YouTube OAuth. "
        "No user viewing history, liked videos, subscriptions, or other "
        "personally identifiable information is requested or stored. "
        "The application's privacy policy (https://verdent.app/privacy) "
        "explicitly states:",
        S["Body"]))

    privacy_items = [
        "We do not collect YouTube user account data.",
        "We do not store API responses beyond the 24-hour cache window.",
        "Cached data is stored locally on the user's device and is never "
        "transmitted to Verdent servers.",
        "Users may clear the local cache at any time via the application Settings.",
    ]
    for item in privacy_items:
        story.append(Paragraph(f"&bull; &nbsp; {item}", S["BulletItem"]))

    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("<b>5.3  Prohibited Use Confirmation</b>", S["H2"]))
    story.append(Paragraph(
        "Verdent confirms that it does NOT engage in any of the following "
        "activities prohibited by the YouTube API Services Terms of Service:",
        S["Body"]))

    prohibited = [
        "Using API data to build a competing video-hosting or streaming platform.",
        "Bypassing or circumventing YouTube's advertising systems.",
        "Using the API to facilitate spam, fraud, or manipulation of engagement metrics.",
        "Storing API data for longer than permitted under the data deletion requirements.",
        "Accessing non-public data without appropriate OAuth authorisation.",
        "Embedding YouTube content outside of the YouTube player in violation of policy.",
    ]
    proh_rows = [[Paragraph(f"&bull; &nbsp; {p}", S["BodySmall"]), "Confirmed Not Done"]
                 for p in prohibited]
    proh_t = Table(proh_rows, colWidths=[12.5*cm, 3.5*cm])
    proh_t.setStyle(TableStyle([
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("LEADING",       (0, 0), (-1, -1), 13),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [colors.white, colors.HexColor("#F3E5F5")]),
        ("GRID",          (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TEXTCOLOR",     (1, 0), (1, -1), GREEN),
        ("FONTNAME",      (1, 0), (1, -1), "Helvetica-Bold"),
        ("ALIGN",         (1, 0), (1, -1), "CENTER"),
    ]))
    story.append(proh_t)

    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph(
        "<b>Developer Acknowledgement</b>",
        S["H2"]))
    story.append(Paragraph(
        "The developer and operator of Verdent acknowledges that the application "
        "has been built and is operated in full compliance with the YouTube API "
        "Services Terms of Service, the YouTube API Services Developer Policies, "
        "and Google's Privacy Policy. The developer agrees to promptly address "
        "any compliance concerns raised by Google and to update the application "
        "as required to maintain compliance with future policy changes.",
        S["Legal"]))

    story.append(Spacer(1, 0.4*cm))

    sig_rows = [
        ["Developer / Operator:", "Verdent Development Team"],
        ["Contact Email:",        "developer@verdent.app"],
        ["Application URL:",      "https://verdent.app"],
        ["Report Date:",          "June 2026"],
        ["Signature:",            "________________________________"],
    ]
    sig_t = Table(sig_rows, colWidths=[4.5*cm, 11.5*cm])
    sig_t.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",      (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 0), (-1, -1), 10),
        ("LEADING",       (0, 0), (-1, -1), 15),
        ("TEXTCOLOR",     (0, 0), (0, -1), MEDIUM),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [colors.white, LIGHT_BG]),
        ("BOX",           (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, BORDER),
    ]))
    story.append(sig_t)

    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        "This document was generated programmatically by the Verdent compliance "
        "reporting system. For questions, contact developer@verdent.app.",
        S["Footer"]))

    return story


def add_page_numbers(canvas_obj, doc):
    """Draw page number footer on every page except the cover."""
    canvas_obj.saveState()
    page_num = canvas_obj.getPageNumber()
    if page_num > 1:
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.setFillColor(colors.HexColor("#999999"))
        canvas_obj.drawString(2.5*cm, 1.2*cm,
                              "Verdent — YouTube API Services Compliance Report")
        canvas_obj.drawRightString(A4[0] - 2.5*cm, 1.2*cm,
                                   f"Page {page_num}")
        canvas_obj.setStrokeColor(colors.HexColor("#DDDDDD"))
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(2.5*cm, 1.5*cm, A4[0] - 2.5*cm, 1.5*cm)
    canvas_obj.restoreState()


def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=A4,
        topMargin=2.2*cm,
        bottomMargin=2.2*cm,
        leftMargin=2.5*cm,
        rightMargin=2.5*cm,
        title="YouTube API Services Compliance Report — Verdent",
        author="Verdent Development Team",
        subject="YouTube API Services Compliance Verification",
    )
    styles = build_styles()
    story = build_story(styles)
    doc.build(story, onFirstPage=add_page_numbers, onLaterPages=add_page_numbers)
    print(f"PDF generated: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
