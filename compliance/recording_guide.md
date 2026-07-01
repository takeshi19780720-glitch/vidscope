# Verdent Compliance Screencast — Recording Guide

## Overview
This guide walks you through recording the compliance screencast for YouTube API Services
review using QuickTime Player on macOS. Target length: **5–8 minutes**.

---

## Pre-Flight Checklist

Before you start recording, complete every item below:

- [ ] The app is running: `cd /Users/takeshikinoshita/Documents/Verdent && uvicorn app.main:app --port 8000`
- [ ] Verify the app is reachable: open `http://localhost:8000/?duration=short` in Safari or Chrome
- [ ] Set browser zoom to **100 %** (Cmd + 0) for a clean display
- [ ] Close all other browser tabs and unrelated applications
- [ ] Set display resolution to **1920 × 1080** or **2560 × 1440** (System Settings → Displays)
- [ ] Ensure microphone is selected: System Settings → Sound → Input → choose your mic
- [ ] Do a 15-second test recording in QuickTime to confirm audio is clear
- [ ] Silence phone notifications (Focus / Do Not Disturb mode ON)
- [ ] Have the narration script open on a **second monitor or device** (not on the recorded screen)

---

## QuickTime Player Setup

1. Open **QuickTime Player** (Spotlight → QuickTime Player)
2. Menu bar → **File → New Screen Recording**
3. Click the **dropdown arrow** (▼) next to the record button
4. Under **Microphone**, select your microphone
5. (Optional) Check **Show Mouse Clicks in Recording** for clarity
6. Click **Record**
7. When prompted, click **"Record Entire Screen"** or drag to select your browser window
8. The 3-second countdown begins — take a breath and start narrating at the opening line

---

## Recording Steps (follow the narration script)

### Step 1 · Introduction (0:00 – 0:45)
- URL already loaded: `http://localhost:8000/?duration=short`
- Pause briefly before speaking so the first frame shows a clean app state

### Step 2 · Application Overview (0:45 – 1:30)
- Slowly scroll the page from top to bottom
- Pause on any visible filter controls to highlight them

### Step 3 · Keyword Search Demo (1:30 – 2:30)
- Click the search input field
- Type **gaming** (spell it out slowly for clarity)
- Click the Search button (or press Enter)
- Wait for results to fully load before continuing narration

### Step 4 · Search Results & Analytics (2:30 – 4:00)
- Scroll through the result cards slowly
- Point the mouse cursor at each data field as you name it
- Scroll down to any chart / graph section

### Step 5 · API Usage & Quota Management (4:00 – 5:30)
- Open a **new browser tab** and navigate to `http://localhost:8000/api/quota`
  — this shows the live JSON: `{"used": N, "limit": 10000, "date": "YYYY-MM-DD"}`
- Return to the main tab
- Repeat the **gaming** search — it should return instantly (cache hit)
- Narrate the speed difference

### Step 6 · Data Display & Attribution (5:30 – 6:15)
- Click or hover over a video card to show the link / detail panel
- Demonstrate that clicking a video title would open YouTube.com
  (you may hover without clicking to avoid leaving the page)

### Step 7 · End-User Benefits & Compliance Summary (6:15 – 7:15)
- Return to the full results view
- Keep mouse still or move it gently as you speak the summary

### Step 8 · Sign-off (7:15 – 7:30)
- Allow 1–2 seconds of silence after the final line before stopping recording

---

## Stopping the Recording

1. Press **Cmd + Ctrl + Esc** or click the stop button in the menu bar
2. QuickTime will open a preview window
3. **Trim** if needed: Edit → Trim (drag the yellow handles to cut silence at start/end)
4. Export:
   - **File → Export As → 1080p**
   - Save as: `/Users/takeshikinoshita/Documents/Verdent/compliance/screencast_verdent.mp4`

---

## Post-Recording: Adding Subtitles (optional)

The subtitle file is at:
`/Users/takeshikinoshita/Documents/Verdent/compliance/subtitles_en.srt`

To burn subtitles into the video using FFmpeg (if installed):
```bash
ffmpeg -i compliance/screencast_verdent.mp4 \
  -vf "subtitles=compliance/subtitles_en.srt:force_style='FontSize=22,FontName=Arial,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline=2'" \
  -c:a copy \
  compliance/screencast_verdent_subtitled.mp4
```

Alternatively, upload the .srt file when submitting the video to the YouTube review portal
(subtitles can be attached as a separate file).

---

## Tips for a Clear Recording

| Tip | Reason |
|-----|--------|
| Speak at **80 % of normal pace** | Reviewers may not be native English speakers |
| Pause **1 second** between sentences | Gives subtitle timing room |
| Move the mouse **slowly and deliberately** | Prevents jarring cuts in screen recordings |
| Keep the browser **full-screen** | Maximises API data visibility |
| Use a **headset or external mic** if available | Reduces room echo |

---

## File Locations Summary

| File | Path |
|------|------|
| Narration script | `/Users/takeshikinoshita/Documents/Verdent/compliance/narration_script.md` |
| Subtitle file (SRT) | `/Users/takeshikinoshita/Documents/Verdent/compliance/subtitles_en.srt` |
| Recording guide (this file) | `/Users/takeshikinoshita/Documents/Verdent/compliance/recording_guide.md` |
| **Output video** | `/Users/takeshikinoshita/Documents/Verdent/compliance/screencast_verdent.mp4` |
