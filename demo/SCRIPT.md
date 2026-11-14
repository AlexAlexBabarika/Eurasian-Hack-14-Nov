# Demo video script (1:50)

The submission allows 2 minutes at most. This script is about 270 spoken words, which is 1:50 at a normal pace. For the live pitch see [docs/PITCH.md](../docs/PITCH.md).

## Before recording

- Terminal 1: `make fixture`. Terminal 2: `make demo` (cached replay, so the audit takes about 15 seconds and never fails on Wi-Fi).
- Chrome, one tab on http://localhost:3000, window about 1440 x 900, zoom 110%, bookmarks bar hidden (Cmd+Shift+B), Do Not Disturb on.
- Terminal 3 at the repo root with a large font, cleared, for shot 7.
- Run through once without recording so every page is warm.

## Shots

| # | Time | On screen | Voiceover |
|---|---|---|---|
| 1 | 0:00-0:14 | Landing page, headline visible. Do not click yet. | "Every startup ships a privacy policy written from a template. Then the code adds Mixpanel, Sentry and OpenAI, and the policy never hears about it. ProveryAI checks one against the other." |
| 2 | 0:14-0:30 | Click "Use demo fixture", then Run. The progress timeline fills in. | "Give it a repository, a live site and the policy. It reads the dependencies and matches them against a catalog of vendors, loads the site without clicking anything to see what fires before consent, and extracts what the policy claims." |
| 3 | 0:30-0:55 | Matrix appears. Click **EU x Personal data** (red). Show the policy quote next to `src/lib/analytics.ts:1`, then the Law tab, then the fix with its copy button. | "The result is a matrix: three jurisdictions, four areas of law. EU, personal data: red. The policy says 'We never share your data with third parties.' The code imports Mixpanel, and five more vendors receive personal data. Every finding links to the official text, here GDPR Article 13, and comes with a clause you can paste into the policy." |
| 4 | 0:55-1:10 | Close the panel. Scroll to the "Tracking before consent" finding: chips read UK amber, EU red, KZ amber. | "Same evidence, different law. Analytics before consent is red in the EU and amber in the UK, where a 2025 amendment added an exception for statistical cookies. The status comes from rules in code. The model only writes the explanation." |
| 5 | 1:10-1:20 | Click **KZ x AI transparency** (red). | "Kazakhstan: chat text goes to OpenAI and the policy never mentions AI. That maps to Kazakhstan's AI law, in force since January 2026." |
| 6 | 1:20-1:33 | Run again with the fixed policy (`http://localhost:4100/privacy-fixed.html`). Before/after view. | "Paste the suggested clauses and run it again. AI transparency turns green. Two findings remain, trackers before consent and an email in the logs. Those need a code change, and the report says so." |
| 7 | 1:33-1:43 | Terminal: `make audit repo=demo/fixture-app policy=demo/fixture-app/privacy.html` prints the red matrix and "Failed: at least one cell is red". | "The same audit is a command line tool, a GitHub Action that fails the pull request, and an MCP tool for coding agents." |
| 8 | 1:43-1:50 | Back to the landing page or the matrix. | "ProveryAI. Trust the policy, but verify the code. It is not legal advice. It is the evidence you take to your lawyer." |

Wording rule for anything you ad-lib: say "possible inconsistency with", never "violates" or "illegal".

## Recording on a Mac

1. Press **Cmd+Shift+5**. Choose "Record Selected Portion" and drag the frame around the Chrome window (or "Record Selected Window").
2. Click **Options**: Microphone > your mic (AirPods or a headset beat the built-in one), Save to > Desktop, and switch on "Show Mouse Clicks".
3. Click **Record**. Stop with the stop button in the menu bar or Cmd+Ctrl+Esc. The file is a `.mov` on the Desktop.
4. Record shot by shot rather than in one take. A mistake then costs one shot, not the whole video.
5. Join and trim in QuickTime Player: open the first clip, Edit > Add Clip to End for the others, Edit > Trim (Cmd+T) to cut dead time. Drag clips in the timeline to reorder.
6. Export a small MP4 (ffmpeg is installed on this machine):

```sh
ffmpeg -i ~/Desktop/demo.mov -c:v libx264 -crf 22 -preset slow -pix_fmt yuv420p -c:a aac -b:a 128k -movflags +faststart demo.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 demo.mp4    # must be under 120
```

If you would rather record the voice separately: record the screen silently, then QuickTime Player > File > New Audio Recording while watching the video, and combine them:

```sh
ffmpeg -i screen.mov -i voice.m4a -map 0:v -map 1:a -c:v libx264 -crf 22 -pix_fmt yuv420p -c:a aac -shortest demo.mp4
```

7. Upload to YouTube as **Unlisted** (or Loom) and put the link in [SUBMISSION.md](../SUBMISSION.md). Open the link in a private window to check it plays without signing in.

## If something breaks on stage

`make demo` (`DEMO_MODE=cached`) replays `api/data/audits/demo-fixture.json` when the three demo URLs are submitted, and `demo-fixture-fixed.json` when the policy URL is the fixed one. Shot 7 is offline either way. The two demo reports also open with no API at all: `/audit/demo-fixture` and `/audit/demo-fixture-fixed`.
