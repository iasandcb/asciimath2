r"""LaTeX macro name -> AsciiMath2 token tables.

Ground truth for every mapping here is `asciimath-parser`'s SYMBOLMAP
(packages/core/src/symbols.ts on the widcardw/asciimath-parser main branch),
read directly rather than paraphrased from docs. Each table below is
organized by *arity* (how many LaTeX-macro-arguments it consumes), since
that's what the converter needs to dispatch on. Where a tex command has more
than one AsciiMath2 spelling upstream (e.g. `ol`/`overline` both produce
`\overline{}`), the more readable/canonical one was picked for this reverse
mapping — there is no single "right" choice, just a consistent one.

One deliberate exception to "ground truth is SYMBOLMAP, unmodified": the
`le`/`leq`/`leqslant`/`ge`/`geq`/`geqslant` entries below (see the comment at
that table) intentionally diverge from SYMBOLMAP's own `"<="`/`"le"` split, to
match mark-vector's frontend override (`frontend/static/js/markdown.js`) and
SPEC.md's stated grammar rather than the library's un-patched default.
"""

# Zero-argument constants: LaTeX macro name (no backslash) -> AsciiMath2 token.
# Rendered as a bare word/symbol in the output; never takes an argument.
CONST_MACROS: dict[str, str] = {
    # Greek letters
    "alpha": "alpha", "beta": "beta", "gamma": "gamma", "Gamma": "Gamma",
    "delta": "delta", "Delta": "Delta", "epsilon": "epsilon",
    "varepsilon": "varepsilon", "zeta": "zeta", "eta": "eta",
    "theta": "theta", "Theta": "Theta", "vartheta": "vartheta",
    "iota": "iota", "kappa": "kappa", "lambda": "lambda", "Lambda": "Lambda",
    "mu": "mu", "nu": "nu", "xi": "xi", "Xi": "Xi", "pi": "pi", "Pi": "Pi",
    "rho": "rho", "sigma": "sigma", "Sigma": "Sigma", "tau": "tau",
    "upsilon": "upsilon", "phi": "phi", "varphi": "varphi", "Phi": "Phi",
    "chi": "chi", "psi": "psi", "Psi": "Psi", "omega": "omega",
    "Omega": "Omega",

    # Operation symbols
    "ast": "ast", "star": "star", "cdot": "cdot", "backslash": "\\\\",
    "setminus": "setminus", "times": "xx", "ltimes": "|><",
    "rtimes": "><|", "bowtie": "|><|", "div": "-:", "circ": "@",
    "oplus": "o+", "otimes": "ox", "odot": "o.", "sum": "sum",
    "prod": "prod", "wedge": "^^", "bigwedge": "^^^", "vee": "vv",
    "bigvee": "vvv", "cap": "nn", "bigcap": "nnn", "cup": "uu",
    "bigcup": "uuu", "pm": "+-", "mp": "-+",

    # Relations
    "ne": "!=", "neq": "!=", "ll": "<<", "gg": ">>",
    # Deliberately not asciimath-parser's own SYMBOLMAP spelling (which has
    # "<=" -> \leqslant, "le" -> \le) - that's a side effect of the JS
    # library adding "le"/"ge" as extra aliases on top of asciimath.org's
    # original grammar, where "<=" was always \le. SPEC.md section 2.3 calls
    # "le"/"ge" ASCII-safe spellings of the *same* \le/\ge, not a distinct
    # slanted variant, so mark-vector's frontend (markdown.js) overrides
    # asciimath-parser's default to match - this table must produce tokens
    # consistent with that override, not the library's un-patched default.
    # \leqslant/\geqslant collapse into the same token as \le/\geq/\ge/\geq:
    # an accepted loss, since essentially nothing but French/Russian-
    # convention documents uses the slanted form over plain \le/\ge.
    "le": "<=", "leq": "<=", "leqslant": "<=",
    "ge": ">=", "geq": ">=", "geqslant": ">=",
    "prec": "-<", "succ": ">-", "preceq": "-<=", "succeq": ">-=",
    "in": "in", "notin": "!in", "subset": "sub", "supset": "sup",
    "subseteq": "sube", "supseteq": "supe", "equiv": "-=", "cong": "~=",
    "sim": "~", "approx": "~~", "propto": "prop", "complement": "complement",
    "coloneqq": ":=", "eqqcolon": "=:",

    # Logic
    "neg": "not", "lnot": "not", "implies": "=>",
    "rightsquigarrow": "~>", "nrightarrow": "-/->", "nleftarrow": "<-/-",
    "nleftrightarrow": "<-/->", "Longleftarrow": "<==", "iff": "iff",
    "forall": "AA", "exists": "EE", "bot": "_|_", "top": "TT",
    "vdash": "|--", "models": "|==",

    # Calculus / big operators
    "int": "int", "oint": "oint", "iint": "iint", "iiint": "iiint",
    "oiint": "oiint", "oiiint": "oiiint", "partial": "del",
    "nabla": "grad", "infty": "oo", "aleph": "aleph",

    # Dots, misc constants
    "ldots": "...", "dots": "...", "cdots": "cdots", "vdots": "vdots",
    "ddots": "ddots", "diamond": "diamond", "square": "square",
    "emptyset": "O/", "varnothing": "O/", "therefore": ":.",
    "because": ":'", "angle": "/_", "triangle": "/_\\",
    "quad": "quad", "qquad": "qquad",

    # Escaped literal punctuation
    "%": "\\%", "&": "\\&", "_": "\\_", "^": "\\^", "$": "\\$", "#": "\\#",
    "{": "{", "}": "}",

    # Functions (trig, log, ...)
    "lim": "lim", "sin": "sin", "cos": "cos", "tan": "tan", "sinh": "sinh",
    "cosh": "cosh", "tanh": "tanh", "cot": "cot", "sec": "sec", "csc": "csc",
    "arcsin": "arcsin", "arccos": "arccos", "arctan": "arctan",
    "coth": "coth", "sech": "sech", "csch": "csch", "exp": "exp",
    "log": "log", "ln": "ln", "det": "det", "dim": "dim", "gcd": "gcd",
    "lcm": "lcm", "min": "min", "max": "max", "sup": "Sup", "inf": "inf",
    "mod": "mod", "sgn": "sgn", "arg": "arg",

    # Arrows
    "uparrow": "uparrow", "downarrow": "downarrow", "to": "to",
    "rightarrow": "rightarrow", "gets": "<-", "leftarrow": "leftarrow",
    "leftrightarrow": "harr", "Rightarrow": "rArr", "Leftarrow": "lArr",
    "Leftrightarrow": "hArr", "mapsto": "|->",
    "curvearrowleft": "curvArrLt", "curvearrowright": "curvArrRt",
    "circlearrowleft": "circArrLt", "circlearrowright": "circArrRt",
    "rightarrowtail": ">->", "twoheadrightarrow": "->>",

    "hline": "hline",
    "vert": "|", "Vert": "||", "mid": "mid",
}

# One-argument accents / notation: LaTeX macro -> AsciiMath2 unary keyword.
# Emitted as `keyword(arg)`.
ACCENT_MACROS: dict[str, str] = {
    "hat": "hat", "widehat": "Hat",
    "widetilde": "Tilde", "tilde": "tilde",
    "overline": "overline", "bar": "bar",
    "vec": "vec", "overrightarrow": "Vec", "overleftarrow": "Aec",
    "dot": "dot", "ddot": "ddot",
    "underline": "underline",
    "overbrace": "overbrace", "underbrace": "underbrace",
    "cancel": "cancel", "phantom": "phantom",
}

# One-argument fonts: LaTeX macro -> AsciiMath2 unary keyword.
FONT_MACROS: dict[str, str] = {
    "mathbf": "bb", "boldsymbol": "bm", "mathbb": "bbb", "mathcal": "cc",
    "mathfrak": "fr", "mathtt": "tt", "mathsf": "sf", "mathrm": "rm",
    "mathscr": "scr",
}

# Common blackboard-bold single-letter shortcuts: mathbb{X} -> XX.
BLACKBOARD_SHORTCUTS: dict[str, str] = {
    "R": "RR", "N": "NN", "Z": "ZZ", "Q": "QQ", "C": "CC",
}

# One-argument sizing commands.
SIZE_MACROS: dict[str, str] = {
    "tiny": "tiny", "small": "small", "large": "large", "huge": "huge",
}

# Two-argument (both mandatory) macros rendered as `keyword(a)(b)`.
TWO_ARG_MACROS: dict[str, str] = {
    "overset": "overset", "underset": "underset", "stackrel": "stackrel",
}

# \frac and its amsmath siblings: rendered as `a/b` (see render._render_frac).
# Display-style distinctions (dfrac/tfrac/cfrac) are lost - AsciiMath2 has no
# equivalent.
FRAC_MACROS = {"frac", "dfrac", "tfrac", "cfrac"}

# \left<X> / \right<X> delimiter -> AsciiMath2 token to use at that position.
# "." (LaTeX's null/invisible delimiter) is handled separately in code since
# its AsciiMath2 spelling depends on whether it's the left or right side
# (`{:` vs `:}`). Two tables because the same character means different
# things as a bare char vs. as a macro: a literal `|` is a single bar, but
# `\|` (which pylatexenc reports as macro name "|") is a double bar.
DELIM_TOKEN_FROM_CHAR: dict[str, str] = {
    "(": "(", ")": ")",
    "[": "[", "]": "]",
    "|": "|",
    "<": "(:", ">": ":)",
}
DELIM_TOKEN_FROM_MACRO: dict[str, str] = {
    "{": "{", "}": "}",       # macro names for \{ and \}
    "|": "||", "Vert": "||",  # macro names for \| and \Vert
    "vert": "|",
    "langle": "(:", "rangle": ":)",
    "lceil": "|~", "rceil": "~|",
    "lfloor": "|__", "rfloor": "__|",
}

# LaTeX environment name -> (left, right) AsciiMath2 matrix delimiters.
# `cases` gets the left-brace / invisible-right pairing that SPEC.md 2.1
# calls out as the piecewise-function idiom.
MATRIX_ENVIRONMENTS: dict[str, tuple[str, str]] = {
    "matrix": ("{:", ":}"),
    "smallmatrix": ("{:", ":}"),
    "array": ("{:", ":}"),
    "pmatrix": ("(", ")"),
    "bmatrix": ("[", "]"),
    "vmatrix": ("|", "|"),
    "Vmatrix": ("||", "||"),
    "cases": ("{", ":}"),
}

# LaTeX environment names treated as multi-line/aligned (SPEC.md 2.2): rows
# separated by a row break, `&` passed through literally.
ALIGNED_ENVIRONMENTS = {
    "aligned", "align", "align*", "gathered", "gather", "gather*",
    "split", "eqnarray", "eqnarray*", "alignat", "alignat*", "multline",
    "multline*",
}

# Macros with no visual effect on the math itself - dropped silently.
IGNORED_MACROS = {
    "displaystyle", "textstyle", "scriptstyle", "scriptscriptstyle",
    "nonumber", "notag", "allowbreak", "relax", "limits", "nolimits",
    # Manual delimiter-sizing commands (\bigl(, \Bigr], ...). AsciiMath2's
    # own parens always render via \left/\right (auto-sized to their
    # content), so the delimiter that follows one of these already gets
    # sized correctly on its own - keeping the sizing command itself would
    # leave it stranded with no delimiter argument of its own (it's meant to
    # immediately precede one, like `\bigl(`, not stand alone), which is
    # invalid LaTeX.
    "bigl", "bigr", "big", "Bigl", "Bigr", "Big",
    "biggl", "biggr", "bigg", "Biggl", "Biggr", "Bigg",
}

# Macros whose single argument is dropped along with the macro itself.
IGNORED_MACROS_WITH_ARG = {"label", "tag"}

# Pure-spacing macros with no argument (`\,` `\;` `\:` `\!` `\ `) - dropped
# silently (matches existing mark-vector behavior: cosmetic-only, safe to
# elide). `\quad`/`\qquad` are NOT here - AsciiMath2 has direct keywords for
# those (see CONST_MACROS) and they're visible spacing, worth keeping.
SPACING_MACROS = {",", ";", ":", "!", " "}
