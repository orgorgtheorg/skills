---
name: Educational Video
description: "Make a narrated, animated educational video (explainer, lecture, onboarding walkthrough, study-guide-to-video) entirely on this machine: Piper offline voice, Manim scenes timed to every sentence, burned-in captions, one MP4. Use when the user asks for a video that explains something, a tutorial or lecture video, or wants notes turned into a video. Starts by asking what the video is about; delivers a playable `url` artifact plus a download link."
---

# Educational Video

You make a YouTube-quality explainer without a video editor, a GPU, or a cloud
render. Everything runs on this computer: 4 vCPU, 4 GB RAM. That shape decides
the rules below — CPU-only libraries, one heavy process at a time, drafts at
720p, and the final at 1080p.

The scripts in `/.skills/educational-video/scripts/` are the pipeline. Do not
rewrite them; call them. Your creative work is the narration and `scenes.py`.

## The flow, end to end

```
ask_question  → topic, audience, length, voice, must-haves
setup.sh      → manim, piper, static ffmpeg, one voice        (2–4 min, once)
script.py     → SECTIONS = [(id, narration), …]  → doc artifact, ONE approval gate
tts.py        → audio/<id>.wav (Piper, speed-adjusted)
build_timings → timings.json + D arrays per scene
scenes.py     → one Scene per section, timed to D            (the creative work)
render.py -qm → draft frames → verify_frames.py → fix → re-render bad scenes only
render.py -qh → final 1080p, sequential
compose.py    → captions + narration + concat → output/final.mp4
serve_player  → `url` artifact + sandbox: download link
```

## Step 0 — File the task, then ask

Call `update_task` (InProgress) and then `ask_question` in the same turn. Never
start rendering on a guess: a 12-minute video costs ~30 minutes of machine time,
and a wrong audience or length throws all of it away.

Skip any question the user already answered or that a file in `/workspace`
answers (a dropped study guide, a doc, a URL). Ask the rest, in one card:

1. **Topic or source** — `long_text`. "What should the video teach? Paste notes
   or name a file in /workspace if you have one."
2. **Audience** — `choice`: Complete beginner / Knows the basics / Expert refresher / Customers of our product.
3. **Length** — `choice`: ~3 min (one idea) / ~6 min / ~10 min / ~15 min (full lecture).
4. **Voice** — `choice`: Female, warm (Amy) / Male, clear (Lessac) / Male, deep (Ryan). Maps to Piper voices `en_US-amy-medium`, `en_US-lessac-medium`, `en_US-ryan-medium`.
5. **Must include / must avoid** — `text`, optional. Formulas, a product screenshot, a phrase to avoid.
6. **Captions** — `yes_no`, default yes. Burned-in word-by-word captions.

Then end your turn. The answers arrive as a chat message and reopen the task.

## Step 1 — Set up the machine (once)

```bash
mkdir -p /workspace/video/<slug> && cd /workspace/video/<slug>
VOICE=en_US-lessac-medium bash /.skills/educational-video/scripts/setup.sh
```

The script is idempotent. It pip-installs `manim>=0.19` (renders through pyav,
so it needs no ffmpeg binary), `piper-tts`, `imageio-ffmpeg` (a static ffmpeg it
symlinks to `~/.local/bin/ffmpeg`), and downloads one Piper voice (~60 MB). No
sudo, no apt, no LaTeX. It prints whether the ffmpeg build has the `ass` filter;
if it does not, `compose.py` writes `.srt` sidecars instead of burning captions.

If you will fork a worker for the render (see "Who does what"), run setup
**before** forking so the worker inherits the installed tools, and note the
project dir in `/workspace/.orgorg/README-fork.md`.

## Step 2 — Write the narration (`script.py`)

`script.py` in the project dir holds one list:

```python
SECTIONS = [
    ("s01_hook",    "Imagine you're dropped into a video game you've never seen. No tutorial, no hints. ..."),
    ("s02_roadmap", "We'll start with the big picture, then build the core idea, then ..."),
    # ...
]
```

Rules that make it a good video, not a read-aloud doc:

- **Intuition first, formula last.** Every section: a relatable example → visual
  intuition → the concept's name → the formal statement → back to the example.
  Never open a section with a definition or a bullet list.
- **Prezi structure.** Section 2 is a roadmap mind-map of every topic. Return to
  it once or twice to show progress. End with a zoom-out and a dense cheat-sheet
  section.
- **Sizing.** 30–90 s of speech per section. ~6 sections for 3 min, ~9 for 6,
  ~13 for 10, ~19 for 15. Piper speaks ~2.6 words/s; `tts.py` speeds it 1.15×
  by default.
- **Section ids** are `sNN_word` (lowercase, underscored). The scene class is the
  PascalCase form: `s01_hook` → `S01Hook`. `scripts/common.py` derives it.
- **Plain-English gloss for every technical term** the audience may not know, in
  the sentence it first appears.
- Sentences end with `.`, `!` or `?` — the timing map splits on them. Avoid
  abbreviations with periods ("e.g.", "Dr.").

### The one approval gate

Put the narration in a **doc artifact** so the person can edit it in place:

```bash
start-convex && start-docs
cd /workspace/app && npx convex run docs:create '{"title":"<Video title> — narration"}'
npx convex run docs:setMarkdown '{"docId":"<id>","markdown":"..."}'   # one H2 per section
orgorg-artifact add --id video-script --kind doc --title "<Video title> — narration" --route /d/<id>
```

Then `ask_question` with ONE `yes_no`: "Script is in [Narration](artifact:video-script).
Record it as is? (Answer No after editing the doc and I'll use your version.)"
When the answer comes back, `docs:getMarkdown` and rebuild `SECTIONS` from the
doc if they said No. This is the only gate. Do not ask again before delivery.

Before the gate, do the **student review** yourself: reread every paragraph as a
first-time learner and fix concepts used before they are taught, undefined
jargon, "check for yourself" cop-outs, and ordering problems. It takes a minute
and saves a re-render.

## Step 3 — Narrate and time

```bash
python3 /.skills/educational-video/scripts/tts.py --voice en_US-lessac-medium --speed 1.15
python3 /.skills/educational-video/scripts/build_timings.py
```

`tts.py` writes `audio/<id>.wav` per section and prints the total. Piper runs
faster than real time on one core and holds ~150 MB. `build_timings.py` splits
each narration into sentences, spreads the real audio duration across them by
word count, writes `timings.json`, and prints a `D = [...]` array per scene with
the sentence text next to each index. Paste those arrays into `scenes.py`.

**Audio comes first, always.** A scene designed before its audio exists will be
10–40 s too short, and the composition clones its last frame to fill the gap.
That is the frozen-video failure this pipeline is built to prevent.

## Step 4 — Scenes (`scenes.py`)

One `Scene` subclass per section, timed to the sentence array.

```python
from manim import *

BG, CYAN, RED, GREEN, GOLD, PURPLE, ORANGE, GREY = (
    "#0f0f1a", "#00d4ff", "#ff6b6b", "#50fa7b", "#ffd700", "#bd93f9", "#ffb86c", "#6272a4")
config.background_color = BG
FONT = "Liberation Sans"   # installed on this image; never rely on the default font
FLOOR = -2.2               # captions live below this line — keep it empty


def T(s, size=28, color=WHITE, **kw):
    return Text(s, font=FONT, font_size=size, color=color, **kw)


def pad(sc, d, used):
    if d - used > 0.05:
        sc.wait(d - used)


class S01Hook(Scene):
    def construct(self):
        D = [2.68, 1.46, 3.42, 3.42, 1.71]          # from build_timings.py
        # [0] "Imagine you're dropped into a video game..."
        pad_ = RoundedRectangle(width=3, height=1.8, corner_radius=0.2, color=CYAN)
        self.play(FadeIn(pad_), run_time=1.2); pad(self, D[0], 1.2)
        # [1] "No tutorial, no hints."
        q = T("?", 64, GOLD).move_to(pad_)
        self.play(Write(q), run_time=D[1])
        # ...one block per sentence...
        self.wait(0.5)                              # buffer; never FadeOut at the end
```

Per-sentence pattern, by duration of `D[i]`:

| `D[i]`    | Do                                                          |
| --------- | ----------------------------------------------------------- |
| < 0.5 s   | `self.wait(D[i])` or `Indicate` something already on screen |
| 0.5–1.5 s | one `FadeIn`/`Write` with `run_time=D[i]`                   |
| 1.5–4 s   | one animation (~1 s) + `pad()`                              |
| 4–8 s     | 2–3 animations + `pad()`                                    |
| > 8 s     | 3–4 animations that build something + `pad()`               |

Hard rules:

- **Every sentence changes something on screen.** Animations inside a block
  never add up to more than `D[i]`.
- **End with `self.wait(0.5)`, never a `FadeOut`.** The last frame is what gets
  cloned if the video is trimmed; a black last frame becomes black screen.
- **Nothing below `FLOOR`.** Captions are burned into the bottom 15%.
- **No `MathTex`/`Tex`.** There is no LaTeX on this machine. Write formulas as
  `T("Q(s,a) = r + γ · max Q(s′,a′)")` — Unicode math (`γ Σ ∞ → ≤ ² ₜ`) renders
  fine in Liberation Sans. Color parts by building a `VGroup` of several `T()`.
- **Always pass `font=FONT`.** The default Pango font on a bare Linux image
  kerns badly ("No lab els"); the `T()` helper handles it.
- **Use `next_to()` for stacks, not hardcoded y.** Fade out content before
  placing new content in the same zone. Boxes ≤ 9 wide.
- `CurvedArrow` and `stroke_style="dashed"` work on manim ≥ 0.19; no workarounds
  needed.

Reusable pieces worth writing once per project: a `build_mindmap(highlight=i)`
roadmap for the Prezi sections, a grid helper, a simple layered-network helper.

## Step 5 — Render, look, fix, render again

```bash
python3 /.skills/educational-video/scripts/render.py --quality m      # 720p drafts, all scenes
python3 /.skills/educational-video/scripts/verify_frames.py            # verify/<Scene>_{mid,end}.png
```

`render.py` renders **one scene at a time** (never run two renders, or a render
and a compose, at once — 4 GB is the ceiling and Manim peaks near 1 GB at 1080p)
and then prints a video-vs-audio duration table with the frozen-frame total.
Target: `frozen-frame total: 0.0s`; every row `OK`.

Read the PNGs in `verify/` with your read tool. Look for text on text, content
clipped at the frame edge, and anything crossing the caption floor. Fix
`scenes.py`, then re-render only those: `render.py --quality m --only S07Bellman S12Loop`.
Expect two rounds. When the drafts are clean:

```bash
python3 /.skills/educational-video/scripts/render.py --quality h      # 1080p30, ~30–120 s per scene
```

Budget: a 10-minute video is roughly 13 scenes × ~60 s = 15 min of final
rendering on this machine. Say so to the person before you start it.

## Step 6 — Compose

```bash
python3 /.skills/educational-video/scripts/compose.py          # --no-captions if they said no
```

Per section it clones the last frame to cover any gap, burns word-by-word ASS
captions (cyan highlight, opaque box, bottom-center) when the ffmpeg build has
libass, muxes the narration, and trims to the exact audio length with
`-preset veryfast -crf 22`. Then it concatenates with stream copy and writes
`output/final.mp4` plus `output/thumb.png`. No background music: narration only.

## Step 7 — Deliver as artifacts

```bash
cd /workspace/video/<slug>
nohup python3 /.skills/educational-video/scripts/serve_player.py --port 5180 --title "<Video title>" > player.log 2>&1 &
orgorg-artifact add --id video-<slug> --kind url --port 5180 --title "<Video title>" --live
```

The player page has the video with the thumbnail as poster and a download link.
In chat, link both ways and show the thumbnail:

```
Done: [<Video title>](artifact:video-<slug>) · [Download MP4](sandbox:/workspace/video/<slug>/output/final.mp4)
![Thumbnail](sandbox:/workspace/video/<slug>/output/thumb.png)
```

Mark the task Done with a one-line `detail` (length, section count). Keep the
`video-script` doc registered so they can request changes against it. A change
request means: edit `script.py`/`scenes.py`, re-run `tts.py --only <id>`, re-time,
re-render `--only` the affected scenes, compose, and `orgorg-artifact touch --id video-<slug>`.

## Who does what (lead vs worker)

Steps 0–3 are quick and conversational: do them yourself. Steps 4–7 are a long
trial-and-error loop that eats context. Hand them to **one** worker on a forked
machine, with a brief that names the project dir, the `D` arrays already in
`timings.json`, the rules in Step 4, and "done" as: `render.py --quality h`
reports 0 s frozen, `verify/` frames are clean, `output/final.mp4` exists, the
`url` artifact is registered and live. Do not start a second render worker for
the same video; two renders on one host starve each other.

## Resource rules (why this fits 4 vCPU / 4 GB)

| Piece    | Tool                                    | Peak RAM       | Notes                                    |
| -------- | --------------------------------------- | -------------- | ---------------------------------------- |
| Voice    | Piper (ONNX, CPU)                       | ~150 MB        | faster than real time; no PyTorch        |
| Scenes   | Manim ≥ 0.19 (pyav, Cairo/Pango wheels) | ~1 GB at 1080p | one scene at a time, `--disable_caching` |
| Encode   | static ffmpeg from imageio-ffmpeg       | ~300 MB        | `veryfast`, 4 threads                    |
| Formulas | Unicode `Text`                          | 0              | no TeX Live (2 GB)                       |

Sequence, never parallel. Drafts at `-qm`, final at `-qh`. Delete `media/`
between projects. If a render is OOM-killed, the scene has too many mobjects on
screen at once: fade earlier content out, or split the section.

## Failure modes

- **Frozen video / black tail** — scene designed before audio, or ends in
  `FadeOut`. Re-time to `D`, hold the last frame.
- **Words with gaps ("A utoen coders")** — `Text()` without `font=FONT`.
- **`ass` filter missing** — the ffmpeg build lacks libass; `compose.py` already
  fell back to `.srt` sidecars. Tell the person captions are a sidecar file.
- **Render slow (> 3 min a scene)** — another process is competing. Check
  `ps`; finish or kill it, then re-render `--only` that scene.
- **`piper` import error** — setup was skipped or ran under a different Python.
  Re-run `setup.sh`.
- **A scene fails to import** — `render.py` prints the last 1500 chars of
  stderr; fix that scene only and re-run with `--only`.
