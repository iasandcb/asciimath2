from dataclasses import dataclass, field


@dataclass(frozen=True)
class Config:
    """Mirrors the three render-time knobs from
    widcardw/asciimath-parser#22 (see SPEC.md section 2.2), plus two
    extension points for macros this package doesn't know about out of the
    box.

    Only `single_newline_break` changes what this library *emits* (it
    controls how many newlines separate rows of a multi-line expression).
    `multiline_env` and `bar_as_mid` are downstream-rendering choices made
    when the AsciiMath2 text is turned back into LaTeX; they're recorded
    here purely so a caller can pass them through to whatever renders the
    AsciiMath2 output, without needing a second place to look them up.

    `custom_macros` and `custom_text` let a caller extend the fixed
    `symbols.py` tables per-conversion without forking this package.
    Neither ever *overrides* a macro this package already gives structural
    meaning to (an ignored sizing command, an accent, a font, ...) - both
    are consulted only where the built-in tables have nothing to say, so an
    empty (default) value is always a strict no-op:

    - `custom_macros`: bare, no-argument LaTeX macro name (no backslash) ->
      AsciiMath2 token, e.g. `{"sqcup": "suu"}` for `\\sqcup`. Consulted only
      for a macro name none of the built-in tables recognize.
    - `custom_text`: exact `\\text{...}`/`\\operatorname{...}`/
      `\\operatorname*{...}` argument content -> AsciiMath2 token, e.g.
      `{"pmf": "pmf"}` to make `\\text{pmf}` emit the bare word `pmf` instead
      of the default quoted `"pmf"` (still correct AsciiMath2, just not
      round-trippable through a renderer that doesn't know `pmf` is a
      symbol of its own). Checked before the default text/operatorname
      handling, since that default has no structural meaning of its own to
      protect.
    """

    multiline_env: str = "aligned"
    single_newline_break: bool = False
    bar_as_mid: bool = True
    custom_macros: dict[str, str] = field(default_factory=dict)
    custom_text: dict[str, str] = field(default_factory=dict)

    @property
    def row_break(self) -> str:
        return "\n" if self.single_newline_break else "\n\n"
