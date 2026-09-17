"""Extends pylatexenc's default macro database with argument specs for
macros it doesn't already know the arity of, so their `{...}` groups are
attached to the macro node (`nodeargd.argnlist`) instead of appearing as
unrelated sibling groups in the node stream.
"""

from pylatexenc import macrospec
from pylatexenc.latexwalker import LatexWalker, get_default_latex_context_db

_EXTRA_MACROS = [
    macrospec.MacroSpec("binom", "{{"),
    macrospec.MacroSpec("dbinom", "{{"),
    macrospec.MacroSpec("tbinom", "{{"),
    macrospec.MacroSpec("overset", "{{"),
    macrospec.MacroSpec("underset", "{{"),
    macrospec.MacroSpec("stackrel", "{{"),
    macrospec.MacroSpec("boldsymbol", "{"),
    # `\operatorname*` is not a distinct macro name to pylatexenc's lexer -
    # macro names never include punctuation, so the lexer always reads just
    # "operatorname" and leaves any "*" as a separate following token. A
    # macro that takes an optional star flag must say so in its own argspec
    # (`*` here) instead of trying to register a second "operatorname*"
    # macro name, which pylatexenc would never actually match (verified: it
    # silently split `\operatorname*{X}` into a zero-arg `\operatorname`
    # plus a stray literal "*" plus an unrelated bare `{X}` group before this
    # fix). The star itself carries no AsciiMath2-visible distinction (same
    # "display-style detail this package doesn't model" trade-off as
    # \dfrac/\tfrac/\cfrac all collapsing to plain `/`), so render.py's
    # `_render_operatorname` just ignores argnlist[0] and reads the mandatory
    # group from argnlist[1].
    macrospec.MacroSpec("operatorname", "*{"),
    macrospec.MacroSpec("pmod", "{"),
    macrospec.MacroSpec("bmod", ""),
    macrospec.MacroSpec("cfrac", "{{"),
    macrospec.MacroSpec("dfrac", "{{"),
    macrospec.MacroSpec("tfrac", "{{"),
    macrospec.MacroSpec("color", "{{"),
    macrospec.MacroSpec("textcolor", "{{"),
    macrospec.MacroSpec("boxed", "{"),
]


def build_context_db() -> macrospec.LatexContextDb:
    db = get_default_latex_context_db()
    db.add_context_category("asciimath2-extra", prepend=True, macros=_EXTRA_MACROS)
    return db


def make_walker(latex: str) -> LatexWalker:
    return LatexWalker(latex, latex_context=build_context_db())
