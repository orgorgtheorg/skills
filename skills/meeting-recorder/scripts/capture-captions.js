#!/usr/bin/env node
/**
 * Tails a meeting's live captions into a transcript file.
 *
 * The sandbox holds no API key, thus it cannot post audio to a speech-to-text
 * service. Every meeting platform already runs speech-to-text for its own
 * caption track, so this reads that: attach to the shared Chrome over CDP, poll
 * the caption container, and append each finished line to a file.
 *
 * Run it detached — it must outlive the turn that starts it:
 *   node /.skills/meeting-recorder/scripts/capture-captions.js \
 *     --url meet.google.com --out /workspace/Recordings/standup.txt &
 *
 * Selectors are a hint, not gospel. Platforms rename classes without notice.
 * When a run reports 0 lines, use --probe to see what the live regions actually
 * are now, pass the right one with --selector, and write the answer into
 * /workspace/memory/general/ so the next meeting starts from it.
 *
 * Usage:
 *   --url <substring>     pick the tab whose URL contains this (required)
 *   --out <path>          transcript file, appended (required)
 *   --selector <css>      caption container, overrides the platform default
 *   --speaker <css>       speaker element inside one entry
 *   --text <css>          text element inside one entry
 *   --probe               print the live regions on the page, then exit
 *   --interval <ms>       poll interval (default 1000)
 *   --quiet-exit <s>      exit after this long with no page (default 120)
 */

const fs = require("fs");
const path = require("path");
const { chromium } = require("/opt/node_modules/playwright");

// Per platform: the container holding caption entries, then the speaker and
// text inside one entry. Several candidates each, because these get renamed;
// the first that matches something on the page wins.
const platforms = [
  {
    match: "meet.google.com",
    name: "Google Meet",
    entry: [
      'div[role="region"][aria-live] > div > div',
      ".nMcdL",
      ".a4cQT div[jsname]",
    ],
    speaker: [".NWpY1d", ".zs7s8d", '[class*="speaker"]'],
    text: [".ygicle", ".iTTPOb", '[class*="text"]'],
  },
  {
    match: "zoom.us",
    name: "Zoom",
    entry: [
      ".live-transcription-subtitle__item",
      "#live-transcription-subtitle",
      ".subtitle-item",
    ],
    speaker: [".live-transcription-subtitle__name", ".subtitle-item__name"],
    text: [".live-transcription-subtitle__text", ".subtitle-item__text"],
  },
  {
    match: "teams.",
    name: "Microsoft Teams",
    entry: [
      '[data-tid="closed-caption-message"]',
      ".ui-chat__item",
      '[class*="captionMessage"]',
    ],
    speaker: ['[data-tid="author"]', ".ui-chat__messageheader"],
    text: ['[data-tid="closed-caption-text"]', ".ui-chat__message__content"],
  },
  {
    match: "webex.com",
    name: "Webex",
    entry: [
      ".caption-item",
      '[class*="closed-caption"] li',
      '[class*="captionItem"]',
    ],
    speaker: [".caption-speaker", '[class*="speakerName"]'],
    text: [".caption-text", '[class*="captionText"]'],
  },
];

function parseArgs(argv) {
  const out = { interval: 1000, quietExit: 120 };
  for (let i = 2; i < argv.length; i += 1) {
    const key = argv[i];
    if (!key.startsWith("--")) {
      continue;
    }
    const name = key.slice(2);
    if (name === "probe") {
      out.probe = true;
      continue;
    }
    out[name] = argv[i + 1];
    i += 1;
  }
  out.interval = Number(out.interval) || 1000;
  out.quietExit = Number(out["quiet-exit"] ?? out.quietExit) || 120;
  return out;
}

const stamp = (ms) => new Date(ms).toISOString().slice(11, 19);

async function findPage(browser, urlPart) {
  for (const context of browser.contexts()) {
    for (const page of context.pages()) {
      if (page.url().includes(urlPart)) {
        return page;
      }
    }
  }
  return null;
}

/**
 * Read the caption entries currently on screen.
 *
 * Captions are not an append-only log: a line grows word by word in place while
 * someone speaks, thus the same entry is read many times before it is final.
 * De-duplication is the caller's job, and it is why this returns whole entries
 * rather than a diff.
 */
async function readEntries(page, sel) {
  return page.evaluate((s) => {
    const firstMatch = (candidates) => {
      for (const candidate of candidates) {
        const found = document.querySelectorAll(candidate);
        if (found.length) {
          return Array.from(found);
        }
      }
      return [];
    };
    const pick = (root, candidates) => {
      for (const candidate of candidates || []) {
        const el = root.querySelector(candidate);
        if (el && el.textContent.trim()) {
          return el.textContent.trim();
        }
      }
      return "";
    };
    return firstMatch(s.entry)
      .map((el) => {
        const speaker = pick(el, s.speaker);
        const text = pick(el, s.text) || (speaker ? "" : el.textContent.trim());
        return { speaker, text: (text || "").replace(/\s+/g, " ").trim() };
      })
      .filter((e) => e.text);
  }, sel);
}

/** Dump anything that looks like a caption region, for when the selectors miss. */
async function probe(page) {
  const regions = await page.evaluate(() => {
    const seen = [];
    document
      .querySelectorAll(
        '[aria-live], [role="log"], [role="region"], [data-tid*="caption"], [class*="caption"], [class*="transcript"], [class*="subtitle"]',
      )
      .forEach((el) => {
        const text = (el.textContent || "").replace(/\s+/g, " ").trim();
        if (!text || text.length > 400) {
          return;
        }
        const cls = typeof el.className === "string" ? el.className : "";
        seen.push({
          tag: el.tagName.toLowerCase(),
          cls: cls.split(/\s+/).filter(Boolean).slice(0, 4).join("."),
          live: el.getAttribute("aria-live") || "",
          tid: el.getAttribute("data-tid") || "",
          sample: text.slice(0, 90),
        });
      });
    return seen.slice(0, 40);
  });
  if (!regions.length) {
    console.log(
      "no candidate regions found — are captions turned ON in the meeting UI?",
    );
    return;
  }
  for (const r of regions) {
    console.log(
      `${r.tag}${r.cls ? "." + r.cls : ""}${r.tid ? ` [data-tid=${r.tid}]` : ""}` +
        `${r.live ? ` [aria-live=${r.live}]` : ""}\n    "${r.sample}"`,
    );
  }
}

async function main() {
  const args = parseArgs(process.argv);
  if (!args.url || (!args.out && !args.probe)) {
    console.error(
      "usage: --url <substring> --out <file> [--selector <css>] [--probe]",
    );
    process.exit(2);
  }

  const browser = await chromium.connectOverCDP("http://127.0.0.1:9223");
  const page = await findPage(browser, args.url);
  if (!page) {
    console.error(
      `no tab matching "${args.url}" — is the meeting open in the shared browser?`,
    );
    process.exit(3);
  }

  if (args.probe) {
    await probe(page);
    await browser.close();
    return;
  }

  const platform = platforms.find((p) => page.url().includes(p.match));
  const sel = {
    entry: args.selector
      ? [args.selector]
      : platform
        ? platform.entry
        : ["[aria-live]"],
    speaker: args.speaker ? [args.speaker] : platform ? platform.speaker : [],
    text: args.text ? [args.text] : platform ? platform.text : [],
  };

  fs.mkdirSync(path.dirname(args.out), { recursive: true });
  const stream = fs.createWriteStream(args.out, { flags: "a" });
  const started = Date.now();
  stream.write(
    `# captions from ${page.url()}\n# started ${new Date(started).toISOString()}\n`,
  );
  console.log(
    `capturing ${platform ? platform.name : "unknown platform"} -> ${args.out}`,
  );

  // A line is written only once it stops growing. `open` holds the entry still
  // being spoken, per speaker; when the text stops being a prefix of itself, the
  // previous version was final.
  const open = new Map();
  const written = new Set();
  let lines = 0;
  let lastSeen = Date.now();

  const flush = (speaker, text) => {
    const key = `${speaker}|${text}`;
    if (!text || written.has(key)) {
      return;
    }
    written.add(key);
    lines += 1;
    stream.write(
      `[${stamp(Date.now() - started)}] ${speaker ? speaker + ": " : ""}${text}\n`,
    );
  };

  const tick = async () => {
    let entries;
    try {
      entries = await readEntries(page, sel);
    } catch (err) {
      // The tab navigated or closed: the meeting is over, or the agent moved.
      if (Date.now() - lastSeen > args.quietExit * 1000) {
        return false;
      }
      return true;
    }
    if (entries.length) {
      lastSeen = Date.now();
    }
    for (const { speaker, text } of entries) {
      const prev = open.get(speaker);
      if (prev && !text.startsWith(prev) && prev.length > text.length) {
        flush(speaker, prev);
      }
      open.set(speaker, text);
    }
    // A speaker whose line is no longer on screen has finished it.
    const live = new Set(entries.map((e) => e.speaker));
    for (const [speaker, text] of open) {
      if (!live.has(speaker)) {
        flush(speaker, text);
        open.delete(speaker);
      }
    }
    return true;
  };

  const stop = () => {
    for (const [speaker, text] of open) {
      flush(speaker, text);
    }
    stream.end(`# ended ${new Date().toISOString()} — ${lines} lines\n`);
    console.log(`${lines} lines -> ${args.out}`);
    process.exit(0);
  };
  process.on("SIGTERM", stop);
  process.on("SIGINT", stop);

  for (;;) {
    const alive = await tick();
    if (!alive) {
      break;
    }
    await new Promise((r) => setTimeout(r, args.interval));
  }
  stop();
}

main().catch((err) => {
  console.error(String(err && err.message ? err.message : err));
  process.exit(1);
});
