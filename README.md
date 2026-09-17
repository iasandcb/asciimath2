# asciimath2

**AsciiMath2** is asciimath.org's grammar extended with everything
[`asciimath-parser`](https://github.com/widcardw/asciimath-parser) already
implements (matrices, aligned multi-line equations, colors, fonts, accents,
...), plus two more contributions on top of that:
[render-time configurability](https://github.com/widcardw/asciimath-parser/pull/22)
and a [symbol-table isolation contract](https://github.com/widcardw/asciimath-parser/pull/21).
The full grammar is written down in **[SPEC.md](https://github.com/iasandcb/asciimath2/blob/main/SPEC.md)** — read that first.

This directory is the standard plus one from-scratch implementation of one
direction through it:

```
LaTeX  --[this package]-->  AsciiMath2  --[asciimath-parser]-->  LaTeX
```

`asciimath-parser` already goes AsciiMath2 → LaTeX. This package goes the
other way, which nothing implemented before. Together they round-trip.

## Install & use

```bash
uv sync            # or: pip install -e .
uv run asciimath2 '\frac{1}{2} + \sqrt{x^2+1}'
# 1/2 + sqrt(x^2 + 1)
```

```python
from asciimath2 import convert, Config, UnsupportedLatexError

convert(r"\sum_{i=1}^n i^2")
# 'sum_(i = 1)^n i^2'

convert(r"\begin{pmatrix} a & b \\ c & d \end{pmatrix}")
# '(a, b; c, d)'

try:
    convert(r"\begin{tikzpicture}...\end{tikzpicture}")
except UnsupportedLatexError:
    ...  # fall back to keeping the original LaTeX -- see "On failure" below
```

`Config` mirrors the three render options from PR #22
(`multiline_env`, `single_newline_break`, `bar_as_mid` — see SPEC.md §2.2);
only `single_newline_break` changes what this package emits.

## How it works

`src/asciimath2/`:

- `latex_context.py` — extends `pylatexenc`'s macro database with argument
  specs for macros it doesn't know the arity of (`\binom`, `\overset`,
  `\operatorname`, ...), so pylatexenc attaches their `{...}` groups as real
  arguments instead of leaving them as unrelated sibling nodes.
- `symbols.py` — the LaTeX-command → AsciiMath2-token tables. Ground truth
  is `asciimath-parser`'s own `SYMBOLMAP`
  (`packages/core/src/symbols.ts`), read directly from source, not
  paraphrased from docs.
- `render.py` — flattens a pylatexenc node tree into a linear token stream,
  then does a single left-to-right pass building AsciiMath2 text. `^`/`_`
  bind to exactly the token before/after them; any compound expression used
  as a required single argument gets wrapped in `(...)`, which AsciiMath2's
  own grammar strips invisibly in exactly those positions — so this
  converter never has to reimplement LaTeX operator precedence itself.
- `cli.py` — `asciimath2 '<latex>'` / reads stdin.

## Scope, honestly

This is a broad, tested common subset of LaTeX math — not a general LaTeX
interpreter (that's not a well-defined target; LaTeX can define arbitrary
macros). What's covered: arithmetic, fractions/roots, sub/superscripts,
`\left`/`\right` delimiters (all standard pairs), big operators with limits,
trig/log/etc. functions, Greek letters, relations/logic/arrows, fonts and
accents, `\text`, `\binom`/`\operatorname`/`\pmod`/`\color`, and matrix-like
and aligned-like environments (`pmatrix`/`bmatrix`/`vmatrix`/`Vmatrix`/
`matrix`/`array`/`cases`, `aligned`/`align`/`gather`/`split`/...).

Two deliberate choices about what happens outside that:

- **`tex(...)` escape hatch** — an unrecognized *bare* macro with no
  arguments (e.g. `\digamma`) degrades to `tex(\digamma)`, AsciiMath2's own
  raw-LaTeX passthrough (SPEC.md §2.4), rather than failing the whole
  expression.
- **On failure, raise, don't guess** — anything else unsupported (an unknown
  macro that's ambiguous about whether it takes arguments, an unrecognized
  environment, a `\left` with no matching `\right`, ...) raises
  `UnsupportedLatexError` for the *whole* expression rather than silently
  emitting something plausible-looking but wrong. This is the same contract
  mark-vector's current `backend/app/latex_to_asciimath.py` already expects
  from `py-asciimath` (`None`/exception on failure → keep the original LaTeX
  visible via `\(...\)`/`\[...\]`), so this package is a drop-in candidate
  for that integration point if/when it's wired in — see "Not yet done"
  below.

## Integration status

Both follow-ups from the initial version of this package are now done:

- **Wired into mark-vector's backend.** `backend/app/latex_to_asciimath.py`
  uses this package (added as a local editable dependency in
  `backend/pyproject.toml`) instead of `py-asciimath` — which is the whole
  reason this package exists (`py-asciimath` couldn't do matrices, `\\`,
  and other constructs this package handles). Multi-row output (aligned
  systems, etc.) is preserved as blank-line-separated rows inside the
  `$$...$$` block it writes back to the document, rather than being
  collapsed to one line, so the row structure survives to the frontend.
- **Frontend renders AsciiMath2's extensions.** `frontend/static/js/markdown.js`
  imports `asciimath-parser` directly as an ES module from jsDelivr
  (`https://cdn.jsdelivr.net/npm/asciimath-parser@<version>/dist/index.js` —
  it ships no browser-global/UMD build, unlike the `asciimath2tex` package it
  replaced) instead of `asciimath2tex`, which only implemented the base
  asciimath.org grammar. For the AsciiMath dialect, a full `$$...$$` block is
  now handed to the parser in one call rather than being split line-by-line,
  so `asciimath-parser`'s own row/`&`-alignment handling (SPEC.md §2.2) does
  the work instead of the frontend approximating it with a `gathered`
  environment. The LaTeX dialect's per-line `gathered` stacking is
  unchanged, since LaTeX has no equivalent convention.

Verified end to end (`asciimath2.convert()` output fed through the actual
published `asciimath-parser@0.6.11` and, in a real browser via Playwright,
through KaTeX) for derivatives/limits, matrix multiplication, aligned
systems of equations, piecewise `cases`, and norms — no parse errors,
correct LaTeX, correct rendering.
