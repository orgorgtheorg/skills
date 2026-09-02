import { useMemo } from "react";
import katex from "katex";

// Math rendering for agent-built apps. Copy this file to
// /workspace/app/src/components/ui/math.tsx and import
// "katex/dist/katex.min.css" once in main.tsx. Depends only on `katex`.
//
// LaTeX that fails to parse is shown in place instead of throwing, so a rough
// transcription never crashes the app. KaTeX output is safe HTML; plain-text
// segments in <MathText> are escaped below.

type MathProps = {
  /** A single LaTeX expression, e.g. "\\int_0^1 x^2\\,dx". */
  children: string;
  /** Render as a centered block instead of inline. */
  display?: boolean;
  className?: string;
};

/** Render one LaTeX expression. */
export function Math({ children, display = false, className }: MathProps) {
  const html = useMemo(
    () =>
      katex.renderToString(children, {
        displayMode: display,
        throwOnError: false,
      }),
    [children, display],
  );
  return display ? (
    <div className={className} dangerouslySetInnerHTML={{ __html: html }} />
  ) : (
    <span className={className} dangerouslySetInnerHTML={{ __html: html }} />
  );
}

const DELIMITERS: { open: string; close: string; display: boolean }[] = [
  { open: "$$", close: "$$", display: true },
  { open: "\\[", close: "\\]", display: true },
  { open: "\\(", close: "\\)", display: false },
  { open: "$", close: "$", display: false },
];

function escapeHtml(s: string): string {
  return s.replace(/[&<>]/g, (c) =>
    c === "&" ? "&amp;" : c === "<" ? "&lt;" : "&gt;",
  );
}

// Turn prose that contains inline math into HTML. Plain text stays text
// (HTML-escaped); each delimited span becomes rendered math. At each position
// the earliest opening delimiter wins, and `$$` beats `$` on a tie because it
// is listed first.
function renderMathText(input: string): string {
  const out: string[] = [];
  let i = 0;
  while (i < input.length) {
    let best: { idx: number; tok: (typeof DELIMITERS)[number] } | null = null;
    for (const tok of DELIMITERS) {
      const idx = input.indexOf(tok.open, i);
      if (idx !== -1 && (best === null || idx < best.idx)) {
        best = { idx, tok };
      }
    }
    if (best === null) {
      out.push(escapeHtml(input.slice(i)));
      break;
    }
    out.push(escapeHtml(input.slice(i, best.idx)));
    const contentStart = best.idx + best.tok.open.length;
    const closeIdx = input.indexOf(best.tok.close, contentStart);
    if (closeIdx === -1) {
      // No closing delimiter — treat the remainder as plain text.
      out.push(escapeHtml(input.slice(best.idx)));
      break;
    }
    out.push(
      katex.renderToString(input.slice(contentStart, closeIdx), {
        displayMode: best.tok.display,
        throwOnError: false,
      }),
    );
    i = closeIdx + best.tok.close.length;
  }
  return out.join("");
}

type MathTextProps = {
  /** Text that CONTAINS inline math in $…$, $$…$$, \(…\) or \[…\] delimiters —
   *  e.g. a problem statement extracted from a PDF. */
  children: string;
  className?: string;
};

/** Render prose with inline math. */
export function MathText({ children, className }: MathTextProps) {
  const html = useMemo(() => renderMathText(children), [children]);
  return (
    <div className={className} dangerouslySetInnerHTML={{ __html: html }} />
  );
}
