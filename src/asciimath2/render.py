r"""LaTeX node tree -> AsciiMath2 text.

Architecture: a pylatexenc node list is first flattened into a linear
sequence of small `FlatToken`s (letters, digit runs, single punctuation
characters, `^`/`_` markers, and opaque macro/group/environment/specials
nodes). A single left-to-right pass over that sequence then builds the
AsciiMath2 output, handling superscript/subscript binding and `\left...
\right` delimiter matching along the way.

This mirrors, deliberately, how AsciiMath2 itself is grammatically built
(see SPEC.md section 2): `^`/`_` bind to exactly the single token before/
after them, and any compound expression used as a required single argument
(an exponent, a `\frac` numerator, an accent's operand, ...) is wrapped in
`(...)` -- which AsciiMath2's own grammar strips invisibly in exactly those
contexts. That means this converter never has to compute LaTeX's operator
precedence itself; it only has to know when it's producing "one argument"
vs. "a top-level sequence of atoms", and let AsciiMath2's grammar do the
rest once the text is parsed downstream.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from pylatexenc.latexwalker import (
    LatexCharsNode,
    LatexCommentNode,
    LatexEnvironmentNode,
    LatexGroupNode,
    LatexMacroNode,
    LatexMathNode,
    LatexSpecialsNode,
)

from .config import Config
from .errors import UnsupportedLatexError
from .latex_context import make_walker
from . import symbols as S

_CHARS_TOKEN_RE = re.compile(r"\s+|!!|\d+(?:\.\d+)?|\^|_|[A-Za-z]|.", re.DOTALL)

# Macro names with a dedicated code path in `render_macro_node` that isn't
# already covered by one of the symbols.py tables. Used to tell "genuinely
# unknown macro" apart from "known macro, just not table-driven" -- see
# `_render_base`'s adjacent-brace-group guard below.
_SPECIAL_CASED_MACROS = {
    "sqrt", "binom", "dbinom", "tbinom", "text", "mbox", "operatorname",
    "pmod", "bmod", "color", "textcolor", "prime", "boxed",
}


@dataclass
class FlatToken:
    kind: str  # LETTER, DIGITS, OP, SUP, SUB, MACRO, GROUP, ENV, SPECIALS, ROWBREAK
    value: Any = None  # str for LETTER/DIGITS/OP, else the pylatexenc node


def _tokenize_chars(chars: str) -> list[FlatToken]:
    tokens: list[FlatToken] = []
    for m in _CHARS_TOKEN_RE.finditer(chars):
        text = m.group()
        if text.isspace():
            continue
        if text == "^":
            tokens.append(FlatToken("SUP"))
        elif text == "_":
            tokens.append(FlatToken("SUB"))
        elif text == "!!" or (len(text) > 1 and text[0].isdigit()):
            tokens.append(FlatToken("OP" if text == "!!" else "DIGITS", text))
        elif len(text) == 1 and text.isalpha():
            tokens.append(FlatToken("LETTER", text))
        else:
            tokens.append(FlatToken("OP", text))
    return tokens


# `asciimath-parser`'s own grammar reads a bare `+`/`-` as a valid start of
# a *new* unary-prefixed expression, not just a standalone atom - so as a
# `^`/`_` argument specifically, `X^+ Y` parses as `X^(+Y)`, silently
# swallowing whatever comes after into the exponent (verified against the
# actual published `asciimath-parser` package; `X^2 Y` / `X^a Y` have no
# such reading and correctly stop at one token). `_render_base` reports
# `atomic=True` for a lone "+"/"-" like any other single token, since that's
# correct everywhere *except* this one context - so the "does this argument
# need `(...)`" decision is made here, at the two places that actually turn
# a rendered piece into a script argument, rather than by second-guessing
# atomicity inside `_render_base` itself.
def _script_arg(arg: str, atomic: bool) -> str:
    if atomic and arg not in ("+", "-"):
        return arg
    return f"({arg})"


class Converter:
    def __init__(self, config: Config | None = None):
        self.cfg = config or Config()

    # -- top level ---------------------------------------------------

    def convert(self, latex: str) -> str:
        walker = make_walker(latex)
        nodes, _, _ = walker.get_latex_nodes()
        return self._render_row_split_block(nodes).strip()

    # -- node list flattening ----------------------------------------

    def flatten(self, nodelist) -> list[FlatToken]:
        tokens: list[FlatToken] = []
        for node in nodelist:
            if isinstance(node, LatexCharsNode):
                tokens.extend(_tokenize_chars(node.chars))
            elif isinstance(node, LatexCommentNode):
                continue
            elif isinstance(node, LatexMacroNode):
                if node.macroname == "\\":
                    tokens.append(FlatToken("ROWBREAK", node))
                else:
                    tokens.append(FlatToken("MACRO", node))
            elif isinstance(node, LatexGroupNode):
                tokens.append(FlatToken("GROUP", node))
            elif isinstance(node, LatexEnvironmentNode):
                tokens.append(FlatToken("ENV", node))
            elif isinstance(node, LatexSpecialsNode):
                tokens.append(FlatToken("SPECIALS", node))
            elif isinstance(node, LatexMathNode):
                tokens.extend(self.flatten(node.nodelist))
            elif node is None:
                continue
            else:
                raise UnsupportedLatexError(type(node).__name__)
        return tokens

    # -- rendering a flat token sequence -------------------------------

    def render_nodelist(self, nodelist) -> tuple[str, bool]:
        return self.render_flat(self.flatten(nodelist))

    def render_flat(self, tokens: list[FlatToken]) -> tuple[str, bool]:
        pieces: list[str] = []
        i = 0
        n = len(tokens)
        while i < n:
            tok = tokens[i]
            if tok.kind in ("SUP", "SUB"):
                # Stray leading script with no base (malformed input) --
                # degrade gracefully instead of raising.
                i += 1
                arg, atomic, i = self._render_base(tokens, i, bare=False)
                op = "^" if tok.kind == "SUP" else "_"
                pieces.append(f"{op}{_script_arg(arg, atomic)}")
                continue
            piece, _atomic, i = self._render_base(tokens, i)
            piece, i = self._absorb_scripts(tokens, i, piece)
            # Dropped macros (pure spacing, \label, ...) render as "" -- skip
            # them rather than leaving a stray joining space in the output.
            if piece != "":
                pieces.append(piece)
        return " ".join(pieces), len(pieces) == 1

    def _absorb_scripts(self, tokens: list[FlatToken], i: int, base: str) -> tuple[str, int]:
        n = len(tokens)
        while i < n and tokens[i].kind in ("SUP", "SUB"):
            op = "^" if tokens[i].kind == "SUP" else "_"
            i += 1
            arg, atomic, i = self._render_base(tokens, i, bare=False)
            base = f"{base}{op}{_script_arg(arg, atomic)}"
        return base, i

    def _render_base(
        self, tokens: list[FlatToken], i: int, bare: bool = True
    ) -> tuple[str, bool, int]:
        """Renders exactly one base unit (no script absorption of its own).

        `bare=True` (the default) is for a unit appearing directly in a
        top-level sequence of atoms: a bare `{...}` group there needs
        invisible-delimiter wrapping (`render_bare_group`) to preserve its
        grouping. `bare=False` is for a unit being consumed as a `^`/`_`
        argument, where the caller already wraps non-atomic results in
        `(...)` itself -- using `render_bare_group` there too would double
        up the grouping (`{: ... :}` around what's about to become `(...)`).
        """
        if i >= len(tokens):
            return "", True, i
        tok = tokens[i]
        if tok.kind in ("LETTER", "DIGITS", "OP"):
            # A bare "|" about to take a `^`/`_` script is LaTeX's
            # `\big|_{X}` restriction notation ("f restricted to X"),
            # reaching here as a lone "|" character token (`\big` itself is
            # a dropped sizing macro - see IGNORED_MACROS)
            # immediately followed by a SUB/SUP token. asciimath-parser's
            # grammar doesn't accept a subscript directly on a bare "|"
            # (verified against the published package: `X|_(Y)` drops the
            # subscript entirely, rendering "Y" as an unrelated bare group
            # right after instead of attaching it) - "mid" (`\mid`) is
            # visually the same vertical bar and *does* parse as a normal
            # scriptable atom, so substitute it only in this exact
            # position; a "|" anywhere else (absolute value, "such that",
            # ...) is untouched.
            if (
                tok.kind == "OP"
                and tok.value == "|"
                and i + 1 < len(tokens)
                and tokens[i + 1].kind in ("SUP", "SUB")
            ):
                return "mid", True, i + 1
            return tok.value, True, i + 1
        if tok.kind == "GROUP":
            if bare:
                text, atomic = self.render_bare_group(tok.value.nodelist)
            else:
                text, atomic = self.render_nodelist(tok.value.nodelist)
            return text, atomic, i + 1
        if tok.kind == "ENV":
            return self.render_environment(tok.value), True, i + 1
        if tok.kind == "SPECIALS":
            return self._render_specials(tok.value), True, i + 1
        if tok.kind == "ROWBREAK":
            # A stray `\\` where a single argument was expected: nothing
            # sensible to render; treat as an empty atom.
            return "", True, i + 1
        if tok.kind == "MACRO":
            node = tok.value
            if node.macroname == "left":
                return self._render_left_right(tokens, i)
            if (
                not self._is_known_macro(node.macroname)
                and i + 1 < len(tokens)
                and tokens[i + 1].kind == "GROUP"
            ):
                # pylatexenc has no argument spec for this macro, so a
                # `{...}` right after it was never attached as *its*
                # argument -- it's a separate sibling group. That's
                # ambiguous: the macro may genuinely take no arguments (in
                # which case the group is unrelated bare grouping), or it
                # may be an arity we just don't know (in which case treating
                # the group as unrelated would silently drop the macro's
                # real argument). Refuse rather than guess.
                raise UnsupportedLatexError(
                    f"\\{node.macroname}",
                    "unknown macro immediately followed by a brace group "
                    "of unknown arity",
                )
            return self.render_macro_node(node), True, i + 1
        raise UnsupportedLatexError(f"token kind {tok.kind}")

    def _is_known_macro(self, name: str) -> bool:
        return (
            name in S.IGNORED_MACROS
            or name in S.IGNORED_MACROS_WITH_ARG
            or name in S.SPACING_MACROS
            or name in S.CONST_MACROS
            or name in S.FRAC_MACROS
            or name in S.ACCENT_MACROS
            or name in S.FONT_MACROS
            or name in S.SIZE_MACROS
            or name in S.TWO_ARG_MACROS
            or name in _SPECIAL_CASED_MACROS
            or name in self.cfg.custom_macros
        )

    # -- arguments / bare grouping -------------------------------------

    def render_argument(self, nodelist) -> str:
        """Renders `nodelist` for use as a single required argument (a
        superscript, a \\frac operand, an accent's operand, ...). AsciiMath2
        strips one layer of `(...)` in exactly these positions, so wrapping
        here is always safe -- it's only skipped when unnecessary."""
        text, atomic = self.render_nodelist(nodelist)
        return text if atomic else f"({text})"

    def render_bare_group(self, nodelist) -> tuple[str, bool]:
        """Renders a `{...}` that is *not* anyone's macro argument -- plain
        LaTeX scope grouping. `(...)` would leave visible parentheses that
        weren't in the source, so invisible-delimiter grouping (`{: :}`) is
        used instead when the content isn't already a single atom."""
        text, atomic = self.render_nodelist(nodelist)
        if atomic:
            return text, True
        return f"{{: {text} :}}", True

    # -- \left ... \right ----------------------------------------------

    def _render_left_right(self, tokens: list[FlatToken], i: int) -> tuple[str, bool, int]:
        assert tokens[i].kind == "MACRO" and tokens[i].value.macroname == "left"
        i += 1
        ldelim, i = self._read_delimiter(tokens, i)
        ldelim = _resolve_null_delimiter(ldelim, is_left=True)
        start = i
        depth = 1
        while i < len(tokens):
            tok = tokens[i]
            if tok.kind == "MACRO" and tok.value.macroname == "left":
                depth += 1
            elif tok.kind == "MACRO" and tok.value.macroname == "right":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        else:
            raise UnsupportedLatexError("\\left", "no matching \\right")
        inner_text, _ = self.render_flat(tokens[start:i])
        i += 1  # skip \right
        rdelim, i = self._read_delimiter(tokens, i)
        rdelim = _resolve_null_delimiter(rdelim, is_left=False)
        return f"{ldelim}{inner_text}{rdelim}", True, i

    def _read_delimiter(self, tokens: list[FlatToken], i: int) -> tuple[str, int]:
        if i >= len(tokens):
            raise UnsupportedLatexError("\\left/\\right", "missing delimiter")
        tok = tokens[i]
        if tok.kind == "OP":
            ch = tok.value
            if ch == ".":
                # Caller distinguishes open/close; "." maps the same way in
                # DELIM_TOKEN_FROM_CHAR is wrong, so handle it directly here
                # via a sentinel resolved by the two call sites below.
                return "\0.", i + 1
            token = S.DELIM_TOKEN_FROM_CHAR.get(ch)
            if token is None:
                raise UnsupportedLatexError(f"delimiter '{ch}'")
            return token, i + 1
        if tok.kind == "MACRO":
            name = tok.value.macroname
            if name == ".":
                return "\0.", i + 1
            token = S.DELIM_TOKEN_FROM_MACRO.get(name)
            if token is None:
                raise UnsupportedLatexError(f"delimiter '\\{name}'")
            return token, i + 1
        raise UnsupportedLatexError("\\left/\\right", "missing delimiter")

    # -- specials (&, ~, ...) --------------------------------------------

    def _render_specials(self, node) -> str:
        ch = node.specials_chars
        if ch == "&":
            return "&"
        if ch in ("~", " "):
            return ""
        raise UnsupportedLatexError(f"specials '{ch}'")

    # -- row/column splitting for environments ---------------------------

    def _split_rows(self, tokens: list[FlatToken]) -> list[list[FlatToken]]:
        rows: list[list[FlatToken]] = []
        current: list[FlatToken] = []
        for tok in tokens:
            if tok.kind == "ROWBREAK":
                rows.append(current)
                current = []
            else:
                current.append(tok)
        rows.append(current)
        return rows

    def _split_cells(self, tokens: list[FlatToken]) -> list[list[FlatToken]]:
        cells: list[list[FlatToken]] = []
        current: list[FlatToken] = []
        for tok in tokens:
            if tok.kind == "SPECIALS" and tok.value.specials_chars == "&":
                cells.append(current)
                current = []
            else:
                current.append(tok)
        cells.append(current)
        return cells

    def _render_row_split_block(self, nodelist) -> str:
        """Used both for the top-level expression and for `aligned`-style
        environments (SPEC.md 2.2): rows separated by `\\`, `&` passed
        through literally within a row."""
        tokens = self.flatten(nodelist)
        rows = self._split_rows(tokens)
        row_texts = [self.render_flat(r)[0] for r in rows]
        while row_texts and row_texts[-1].strip() == "":
            row_texts.pop()
        return self.cfg.row_break.join(row_texts)

    def render_environment(self, node: LatexEnvironmentNode) -> str:
        name = node.environmentname
        if name in S.MATRIX_ENVIRONMENTS:
            return self._render_matrix(node)
        if name in S.ALIGNED_ENVIRONMENTS:
            return self._render_row_split_block(node.nodelist)
        raise UnsupportedLatexError(f"\\begin{{{name}}}")

    def _render_matrix(self, node: LatexEnvironmentNode) -> str:
        ldelim, rdelim = S.MATRIX_ENVIRONMENTS[node.environmentname]
        tokens = self.flatten(node.nodelist)
        rows = self._split_rows(tokens)
        row_strs = []
        for row in rows:
            cells = self._split_cells(row)
            cell_strs = []
            for c in cells:
                text = self.render_flat(c)[0].rstrip()
                # `cases`-style rows conventionally write a literal "," right
                # before the column break (`x^2, & x>0`); AsciiMath2 already
                # uses "," as its own column separator, so keep only one.
                if text.endswith(","):
                    text = text[:-1].rstrip()
                cell_strs.append(text)
            row_strs.append(", ".join(cell_strs))
        while row_strs and row_strs[-1].strip() == "":
            row_strs.pop()
        return f"{ldelim}{'; '.join(row_strs)}{rdelim}"

    # -- macro dispatch ---------------------------------------------------

    def render_macro_node(self, node: LatexMacroNode) -> str:
        name = node.macroname

        if name in S.IGNORED_MACROS or name in S.IGNORED_MACROS_WITH_ARG:
            return ""
        if name in S.SPACING_MACROS:
            return ""
        if name in S.CONST_MACROS:
            return S.CONST_MACROS[name]
        if name == "sqrt":
            return self._render_sqrt(node)
        if name in S.FRAC_MACROS:
            return self._render_frac(node)
        if name in S.ACCENT_MACROS:
            return self._render_one_arg(S.ACCENT_MACROS[name], node)
        if name in S.FONT_MACROS:
            return self._render_font(name, node)
        if name in S.SIZE_MACROS:
            return self._render_one_arg(S.SIZE_MACROS[name], node)
        if name in S.TWO_ARG_MACROS:
            return self._render_two_arg(S.TWO_ARG_MACROS[name], node)
        if name in ("binom", "dbinom", "tbinom"):
            return self._render_binom(node)
        if name in ("text", "mbox"):
            return self._render_text(node)
        if name == "operatorname":
            return self._render_operatorname(node)
        if name == "pmod":
            return self._render_pmod(node)
        if name == "bmod":
            return "mod"
        if name in ("color", "textcolor"):
            return self._render_color(node)
        if name == "prime":
            return "'"
        if name == "boxed":
            return self._render_boxed(node)
        if name in self.cfg.custom_macros:
            return self.cfg.custom_macros[name]
        return self._render_unknown_macro(node)

    def _arg(self, node: LatexMacroNode, idx: int):
        return node.nodeargd.argnlist[idx]

    def _arg_nodelist(self, node: LatexMacroNode, idx: int) -> list:
        return self._as_nodelist(self._arg(node, idx))

    def _as_nodelist(self, arg_node) -> list:
        """A macro argument is a `LatexGroupNode` (has `.nodelist`) only when
        the source wrote it with braces. `\\mathcal B`, `\\sqrt x`, `\\vec\\imath`
        -- all common, especially from LLMs that skip braces on a
        single-token argument -- hand back that one token directly (a
        `LatexCharsNode`, `LatexMacroNode`, ...) instead. Normalize both to
        a plain node list so every caller can just recurse into it."""
        if arg_node is None:
            return []
        nodelist = getattr(arg_node, "nodelist", None)
        return nodelist if nodelist is not None else [arg_node]

    # `keyword(...)` call syntax already supplies its own literal
    # parentheses, so these use plain `render_nodelist` (just the text) and
    # never `render_argument` -- that helper adds its *own* conditional
    # `(...)`, which would double up here (e.g. `frac((a+b))(c)`).

    def _render_sqrt(self, node: LatexMacroNode) -> str:
        args = node.nodeargd.argnlist
        radicand, _ = self.render_nodelist(self._as_nodelist(args[-1]))
        if len(args) > 1 and args[0] is not None:
            index, _ = self.render_nodelist(self._as_nodelist(args[0]))
            return f"root({index})({radicand})"
        return f"sqrt({radicand})"

    def _render_one_arg(self, keyword: str, node: LatexMacroNode) -> str:
        text, _ = self.render_nodelist(self._arg_nodelist(node, 0))
        return f"{keyword}({text})"

    def _render_two_arg(self, keyword: str, node: LatexMacroNode) -> str:
        a, _ = self.render_nodelist(self._arg_nodelist(node, 0))
        b, _ = self.render_nodelist(self._arg_nodelist(node, 1))
        return f"{keyword}({a})({b})"

    def _render_frac(self, node: LatexMacroNode) -> str:
        # `a/b` (AsciiMath2's own division operator, `OperatorAOB` in the
        # reference implementation) strips a redundant `(...)` around each
        # operand exactly like `frac(a)(b)`'s call syntax does, and produces
        # byte-for-byte the same `\frac{...}{...}` downstream - verified
        # against the actual asciimath-parser package. `1/6` reads far more
        # like an actual fraction than `frac(1)(6)`, so prefer it; display
        # style (\dfrac/\tfrac/\cfrac) has no AsciiMath2 equivalent either
        # way, so that distinction is lost the same as it always was.
        a, a_atomic = self.render_nodelist(self._arg_nodelist(node, 0))
        b, b_atomic = self.render_nodelist(self._arg_nodelist(node, 1))
        return f"{a if a_atomic else f'({a})'}/{b if b_atomic else f'({b})'}"

    def _render_binom(self, node: LatexMacroNode) -> str:
        a, _ = self.render_nodelist(self._arg_nodelist(node, 0))
        b, _ = self.render_nodelist(self._arg_nodelist(node, 1))
        return f"({a} choose {b})"

    def _render_boxed(self, node: LatexMacroNode) -> str:
        # AsciiMath2 has no framed/boxed construct to map \boxed onto, so
        # the box itself is dropped - only the (still correct) mathematical
        # content survives. Same trade-off as dropping \bigl/\bigr's manual
        # delimiter sizing: losing decoration beats losing the whole
        # expression to UnsupportedLatexError.
        text, _ = self.render_nodelist(self._arg_nodelist(node, 0))
        return text

    def _single_letter(self, nodelist) -> str | None:
        if len(nodelist) != 1 or not isinstance(nodelist[0], LatexCharsNode):
            return None
        s = nodelist[0].chars.strip()
        return s if len(s) == 1 else None

    def _render_font(self, name: str, node: LatexMacroNode) -> str:
        nodelist = self._arg_nodelist(node, 0)
        if name == "mathbb":
            letter = self._single_letter(nodelist)
            if letter in S.BLACKBOARD_SHORTCUTS:
                return S.BLACKBOARD_SHORTCUTS[letter]
        text, _ = self.render_nodelist(nodelist)
        return f"{S.FONT_MACROS[name]}({text})"

    def _extract_plain_text(self, nodelist) -> str:
        parts = []
        for node in nodelist:
            if isinstance(node, LatexCharsNode):
                parts.append(node.chars)
            elif isinstance(node, LatexCommentNode):
                continue
            else:
                parts.append(node.latex_verbatim())
        return "".join(parts)

    def _render_text(self, node: LatexMacroNode) -> str:
        text = self._extract_plain_text(self._arg_nodelist(node, 0))
        text = text.replace('"', "'").strip()
        if text in self.cfg.custom_text:
            return self.cfg.custom_text[text]
        return f'"{text}"'

    def _render_operatorname(self, node: LatexMacroNode) -> str:
        # argnlist[0] is the optional `\*` flag (see latex_context.py) -
        # ignored, since AsciiMath2 has no way to distinguish it anyway.
        text = self._extract_plain_text(self._arg_nodelist(node, 1)).strip()
        if text in self.cfg.custom_text:
            return self.cfg.custom_text[text]
        if "(" in text or ")" in text:
            raise UnsupportedLatexError("\\operatorname", text)
        return f"op({text})"

    def _render_pmod(self, node: LatexMacroNode) -> str:
        inner, _ = self.render_nodelist(self._arg_nodelist(node, 0))
        return f"quad (mod {inner})"

    def _render_color(self, node: LatexMacroNode) -> str:
        name = self._extract_plain_text(self._arg_nodelist(node, 0)).strip()
        content, _ = self.render_nodelist(self._arg_nodelist(node, 1))
        return f"color({name})({content})"

    def _render_unknown_macro(self, node: LatexMacroNode) -> str:
        argnlist = node.nodeargd.argnlist if node.nodeargd else []
        if not any(argnlist):
            verbatim = node.latex_verbatim()
            if "(" not in verbatim and ")" not in verbatim and '"' not in verbatim:
                return f"tex({verbatim})"
        raise UnsupportedLatexError(f"\\{node.macroname}", node.latex_verbatim())


def convert(latex: str, config: Config | None = None) -> str:
    """Converts one LaTeX math expression to AsciiMath2 text.

    Raises `UnsupportedLatexError` if `latex` contains a construct this
    converter doesn't know how to render. Callers that want the
    "best-effort, fall back to raw LaTeX" behavior mark-vector's backend
    already relies on should catch that and keep the original LaTeX.
    """
    return Converter(config).convert(latex)


def _resolve_null_delimiter(text: str, *, is_left: bool) -> str:
    return text.replace("\0.", "{:" if is_left else ":}")
