# AsciiMath2 — an extended AsciiMath standard

Status: draft, v0.1.0 (2026-09-01)

## 1. What this is

[AsciiMath](https://asciimath.org) is a lightweight math markup language with a
small, stable core grammar. In practice, every serious implementation extends
it — matrices, colors, fonts, accents, piecewise functions, aligned multi-line
equations — because the original grammar doesn't cover them. The most complete
of these extensions is [`asciimath-parser`](https://github.com/widcardw/asciimath-parser)
by widcardw (docs: https://asciimath.widcard.win/en/introduction/), which is
explicit that it is "NOT exactly compatible with asciimath.org."

**AsciiMath2 is that extended dialect, written down as one specification.**
It is defined as:

> asciimath.org core grammar
> + everything `asciimath-parser` (main branch) already implements
> + the rendering-configurability contributed in
>   [widcardw/asciimath-parser#22](https://github.com/widcardw/asciimath-parser/pull/22)
>   (`multilineEnv`, `singleNewlineBreak`, `barAsMid`)
> + the correctness contract from
>   [widcardw/asciimath-parser#21](https://github.com/widcardw/asciimath-parser/pull/21)
>   (symbol-table overrides must be scoped per parser instance, never global)

This document is the standard. [`src/asciimath2/`](src/asciimath2/) is a
from-scratch Python implementation of one direction through it: **LaTeX →
AsciiMath2**, i.e. the direction `asciimath-parser` does *not* implement (it
only goes AsciiMath → LaTeX). Together, the pair gives a full LaTeX ⇄
AsciiMath2 round trip when paired with `asciimath-parser` itself for the
other direction.

Everything in this spec that isn't explicitly marked "AsciiMath2 extension" is
inherited unchanged from asciimath.org. Ground truth for the extended parts of
this document was read directly from `asciimath-parser`'s source
(`packages/core/src/{symbols,parser,codegen,trie,index}.ts`), not just its
docs site, since the docs are AI-summarizable but the grammar is not.

## 2. Grammar

Using the same notation as asciimath.org:

```
v  ::= [A-Za-z] | greek letter | numeral | constant symbol   (variable / atom)
u  ::= sqrt | text | bb | bbb | cc | tt | fr | sf | rm | bm | hat | bar | ...
                                                              (unary prefix ops)
b  ::= frac | root | stackrel | overset | underset | color   (binary prefix ops)
l   ::= ( | [ | { | (: | {: | |  (or any left AsciiMath2 delimiter)
r   ::= ) | ] | } | :) | :} | |  (matching right delimiter)
S  ::= v | l E r | u S | b S S | matrix | "text"
I  ::= S_S | S^S | S_S^S | S     (subscript / superscript bind to the
                                   immediately preceding simple expression;
                                   subscript, if present, must come first)
E  ::= I E | I / I | E              (juxtaposition = implicit multiplication;
                                      `/` is left-associative fraction)
```

Whitespace separates tokens but is otherwise not significant. The tokenizer is
maximal-munch over a symbol trie (longest matching key wins), falling back to
single-character variables, so an unrecognized token never breaks the whole
parse — it degrades to a literal.

### 2.1 Matrices — AsciiMath2 extension

asciimath.org's own nested-bracket matrix syntax (`[[a,b],[c,d]]`) is dropped.
AsciiMath2 uses `asciimath-parser`'s row/column syntax instead, because it
also supports partial column dividers, which nested brackets cannot express:

```
[a, b | c; d, e | f]
```

- `,` separates elements within a row
- `;` separates rows
- `|` is an optional *visual* column divider (renders as a vertical rule via
  `\begin{array}{cc|c}`), not a structural separator
- The opening/closing delimiter pair chosen determines the matrix's
  brackets — any AsciiMath2 left/right pair works:

| Delimiters | Renders as |
|---|---|
| `(...)` | parenthesis matrix — `pmatrix` |
| `[...]` | bracket matrix — `bmatrix` |
| `{: ... :}` | no visible delimiter — `matrix`/`array` |
| `\vert ... \vert` (single `\|`) | determinant bars — `vmatrix` |
| `\Vert ... \Vert` (`\|\|`) | double bars — `Vmatrix` |
| `{ ... :}` | left brace only, left-aligned — piecewise/cases |

Example — piecewise function, the canonical AsciiMath2 idiom for `cases`:

```
f(x) = { x^2, if x > 0; 0, otherwise :}
```

### 2.2 Multi-line / aligned expressions — AsciiMath2 extension

A blank line (two consecutive newlines) inside an expression is a row break;
`&` is a literal alignment marker, passed straight through. If the source
contains either token anywhere, the whole expression is wrapped in a
multi-line LaTeX environment on output:

```
a &= b + c

  &= d
```

renders as `\begin{aligned} a &= b + c \\  &= d \end{aligned}`.

**Configurable (PR #22):**

| Config | Default | Effect |
|---|---|---|
| `multilineEnv` | `"aligned"` | LaTeX environment the renderer wraps multi-line output in (e.g. `"gather*"` for unaligned display, no `&` required) |
| `singleNewlineBreak` | `false` | When `true`, a *single* newline is enough to start a new row, instead of requiring a blank line |
| `barAsMid` | `true` | Whether a lone unpaired `\|` (no matching partner found) renders as `\mid`. When `false` it renders as a literal `\|` glyph |

These are renderer options, not grammar changes — the same AsciiMath2 source
text parses identically either way; only the LaTeX it expands to differs.
`asciimath2.Config` records the same three knobs for documentation and
round-trip fidelity, even though only `single_newline_break` affects what the
LaTeX→AsciiMath2 direction emits (the other two are pure rendering choices
made downstream, when AsciiMath2 is turned back into LaTeX).

### 2.3 Symbol-table extension isolation — AsciiMath2 correctness contract (PR #21)

Any implementation that lets callers register custom symbols (an `abs`-style
override, a house-style token, a domain-specific macro) **must** scope that
override to the parser/converter instance it was passed to. A shared,
module-level symbol table mutated in place — the bug PR #21 fixes — makes
one caller's customization leak into every other parser built in the same
process, including ones built *before* the customization existed. This
isn't a style preference: it's the difference between an extension point and
a footgun. Conformance to AsciiMath2 requires the former.

### 2.4 Escape hatch

`tex(...)` embeds a single word or one *unnested* parenthesized/quoted span of
raw LaTeX verbatim — untouched, unparsed. It is the standard's designated
fallback for anything a converter cannot confidently express: better to drop
into raw LaTeX for one sub-expression than to guess and render silently wrong
math. `asciimath2` uses this for isolated unsupported constructs where it's
safe (no parentheses in the raw span to confuse the eater), and falls back to
failing the whole conversion — leaving the original LaTeX in place — when it
isn't.

## 3. Full symbol reference

Everything below is a token recognized by the AsciiMath2 tokenizer. Where a
LaTeX form is common, it's listed after `→`; a bare AsciiMath2 token with no
arrow has no shorter LaTeX equivalent worth naming (it just *is* the LaTeX
command name, unbackslashed).

### Greek letters
`alpha beta gamma Gamma delta Delta epsilon varepsilon zeta eta theta Theta
vartheta iota kappa lambda Lambda mu nu xi Xi pi Pi rho sigma Sigma tau
upsilon phi varphi Phi chi psi Psi omega Omega`

### Operation symbols
| AsciiMath2 | LaTeX | | AsciiMath2 | LaTeX |
|---|---|---|---|---|
| `+` | `+` | | `-` | `-` |
| `*`, `cdot` | `\cdot` | | `**`, `ast` | `\ast` |
| `star` | `\star` | | `//` | `/` (inline) |
| `xx` | `\times` | | `-:` | `\div` |
| `setminus` | `\setminus` | | `@` | `\circ` |
| `o+` | `\oplus` | | `ox` | `\otimes` |
| `o.` | `\odot` | | `sum` | `\sum` |
| `prod` | `\prod` | | `^^`, `^^^` | `\wedge`, `\bigwedge` |
| `vv`, `vvv` | `\vee`, `\bigvee` | | `nn`, `nnn` | `\cap`, `\bigcap` |
| `uu`, `uuu` | `\cup`, `\bigcup` | | `+-`, `-+` | `\pm`, `\mp` |

### Relations
`= != -= ~= ~ ~~ < > <= >= -< >- -<= >-= in !in sub sup sube supe prop
-<= := =:`, plus `lt`/`gt`/`le`/`ge` as ASCII-safe spellings of `< > \le \ge`.

### Logic
`and or not => <=> iff AA EE _|_ TT |-- |==`

### Big operators, calculus
`int oint iint iiint lim sum prod del(=\partial) grad(=\nabla) pp(=\partial,
derivative form) dd(=\mathrm d, derivative form) infty(oo)`

Partial/total derivatives: `pp f x` → `(\partial f)/(\partial x)`; `dd/dx f`
and `(dely)/(delx)` forms are also recognized (see `asciimath-parser`'s
`OperatorPartial` handling for the exact grammar).

### Grouping / fractions / roots
`sqrt(x)`, `root(n)(x)`, `frac(a)(b)` (equivalently `a/b`), `(a choose b)` for
binomial coefficients, `stackrel(a)(b)`, `overset(a)(b)`, `underset(a)(b)`.

### Functions
`sin cos tan sinh cosh tanh cot sec csc arcsin arccos arctan coth sech csch
exp log ln det dim gcd lcm min max Sup inf mod sgn arg abs(x) norm(x)
floor(x) ceil(x)`

### Arrows
`uarr darr rarr(->) larr(<-) harr rArr lArr hArr |-> curvArrLt curvArrRt
circArrLt circArrRt`

### Fonts (all take one argument)
`bb`(mathbf) `bm`(boldsymbol) `bbb`(mathbb) `cc`(mathcal) `tt`(mathtt)
`fr`(mathfrak) `sf`(mathsf) `rm`(mathrm) `scr`(mathscr)

### Accents / notation (one argument)
`hat bar overline ul(underline) vec Vec(overrightarrow) Aec(overleftarrow)
tilde Tilde(widetilde) Hat(widehat) dot ddot obrace(overbrace)
ubrace(underbrace) cancel phantom`

### Text, sizing, spacing
`"literal text"`, `color(name)(expr)`, `tiny small large huge`, `quad qqad`,
`hspace(12pt)`.

### Sets, misc constants
`CC NN QQ RR ZZ O/(emptyset) aleph oo ... cdots vdots ddots square diamond
/_(angle) /_\ (triangle) :.(therefore) :'(because)`

## 4. Compatibility

- Any valid asciimath.org document is a valid AsciiMath2 document — this is a
  superset, not a fork.
- An AsciiMath2 document using only §2.1/§2.2 extensions will render
  incorrectly (or fail) in a strict asciimath.org-only renderer — it needs an
  AsciiMath2-aware one, such as `asciimath-parser` itself. mark-vector's
  frontend (`frontend/static/js/markdown.js`) renders the AsciiMath dialect
  with `asciimath-parser` for exactly this reason.
- §2.2's `singleNewlineBreak` config is PR #22 as proposed, not as shipped:
  the published `asciimath-parser` package (0.6.11 as of this writing)
  doesn't have it yet, so the parser itself still only treats an actual
  blank line as a row break. Since real documents (LLM output especially)
  reliably put one row per physical line but not reliably a blank line
  between them, `markdown.js` doesn't lean on the parser's native
  blank-line detection at all: it splits the source on every newline first,
  treats each non-blank physical line as its own row unconditionally, and
  only then joins them back with blank lines before the one call to the
  parser - so §2.2's `&`-alignment handling still applies per row, it's
  just this module deciding the row boundaries instead of the parser.

## 5. Sources

- https://asciimath.org — base grammar
- https://github.com/widcardw/asciimath-parser (`packages/core/src`, main
  branch as of 2026-08-18) — extended grammar ground truth
- https://asciimath.widcard.win/en/introduction/ — extended grammar docs
- https://github.com/widcardw/asciimath-parser/pull/22 — render-config spec (§2.2)
- https://github.com/widcardw/asciimath-parser/pull/21 — isolation contract (§2.3)
