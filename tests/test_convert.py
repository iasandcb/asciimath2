import pytest

from asciimath2 import Config, UnsupportedLatexError, convert


@pytest.mark.parametrize(
    "latex, expected",
    [
        # Basics
        (r"a + b - c", "a + b - c"),
        (r"2x + 3", "2 x + 3"),
        (r"\alpha + \beta = \gamma", "alpha + beta = gamma"),
        # Fractions / roots
        (r"\frac{1}{2}", "1/2"),
        (r"\frac{a+b}{c}", "(a + b)/c"),
        (r"\sqrt{x}", "sqrt(x)"),
        (r"\sqrt[3]{x}", "root(3)(x)"),
        (r"\sqrt[3]{x^2+1}", "root(3)(x^2 + 1)"),
        # Sub/superscript
        (r"x^2", "x^2"),
        (r"x_1", "x_1"),
        (r"x_1^2", "x_1^2"),
        (r"x^{2n}", "x^(2 n)"),
        (r"e^{-x}", "e^(- x)"),
        (r"x^{\sqrt{2}}", "x^sqrt(2)"),
        # A bare "+"/"-" as a *whole* superscript/subscript (not part of a
        # longer expression like "-x" above) is ambiguous in
        # asciimath-parser's own grammar with the unary +/- starting a new
        # expression - `x^+ y` parses there as `x^(+y)`, silently absorbing
        # "y" into the exponent. Always parenthesizing a lone "+"/"-" script
        # argument avoids that regardless of what follows it.
        (r"x^+", "x^(+)"),
        (r"x^{+}", "x^(+)"),
        (r"A_-", "A_(-)"),
        (r"\Sigma_{n+1}^{+}", "Sigma_(n + 1)^(+)"),
        (r"\sum_{i=1}^{n} i^2", "sum_(i = 1)^n i^2"),
        (r"\lim_{x \to \infty} f(x)", "lim_(x to oo) f ( x )"),
        # Delimiters
        (r"\left( x + y \right)^2", "(x + y)^2"),
        (r"\left| x \right|", "|x|"),
        (r"\left\| v \right\|", "||v||"),
        (r"\left\{ x \right\}", "{x}"),
        (r"\left[ x \right)", "[x)"),
        (r"\left\langle a, b \right\rangle", "(:a , b:)"),
        # Relations / logic / arrows
        (r"a \le b \implies a - c \le b - c", "a <= b => a - c <= b - c"),
        (r"\forall x \in \mathbb{R}, x^2 \ge 0", "AA x in RR , x^2 >= 0"),
        (r"x \ne y", "x != y"),
        (r"a \to b", "a to b"),
        # Functions
        (r"\sin^2 x + \cos^2 x = 1", "sin^2 x + cos^2 x = 1"),
        (r"\log_2 8 = 3", "log_2 8 = 3"),
        (r"\operatorname{sgn}(-3)", "op(sgn) ( - 3 )"),
        # Accents / fonts / text
        (r"\overline{AB}", "overline(A B)"),
        (r"\vec{v}", "vec(v)"),
        (r"\mathbf{v} \cdot \mathbf{w}", "bb(v) cdot bb(w)"),
        (r"\mathbb{R}^n", "RR^n"),
        (r"\mathbb{Z}", "ZZ"),
        (r"\mathcal{L}\{f\}", "cc(L) { f }"),
        (r"\text{hello world}", '"hello world"'),
        # Two-arg macros
        (r"\binom{n}{k}", "(n choose k)"),
        (r"\overset{a}{b}", "overset(a)(b)"),
        (r"\stackrel{a}{b}", "stackrel(a)(b)"),
        (r"\color{red}{x^2}", "color(red)(x^2)"),
        # Primes / factorial pass straight through
        (r"f'(x)", "f ' ( x )"),
        (r"n!", "n !"),
        # \boxed has no AsciiMath2 equivalent (no framed-box construct) -
        # the box is dropped, the content survives.
        (r"\boxed{x = 1}", "x = 1"),
        (r"\boxed{(\Omega,\mathcal F,\mathbb P)}", "( Omega , cc(F) , bbb(P) )"),
    ],
)
def test_expressions(latex: str, expected: str):
    assert convert(latex) == expected


class TestMatrices:
    def test_pmatrix(self):
        assert convert(r"\begin{pmatrix} a & b \\ c & d \end{pmatrix}") == "(a, b; c, d)"

    def test_bmatrix(self):
        assert convert(r"\begin{bmatrix} 1 & 0 \\ 0 & 1 \end{bmatrix}") == "[1, 0; 0, 1]"

    def test_vmatrix_is_determinant_bars(self):
        assert convert(r"\begin{vmatrix} a & b \\ c & d \end{vmatrix}") == "|a, b; c, d|"

    def test_Vmatrix_is_double_bars(self):
        assert convert(r"\begin{Vmatrix} a & b \\ c & d \end{Vmatrix}") == "||a, b; c, d||"

    def test_matrix_env_has_no_visible_delimiter(self):
        assert convert(r"\begin{matrix} a & b \\ c & d \end{matrix}") == "{:a, b; c, d:}"

    def test_single_row(self):
        assert convert(r"\begin{pmatrix} a & b \end{pmatrix}") == "(a, b)"

    def test_cases_is_left_brace_only(self):
        got = convert(
            r"\begin{cases} x^2, & x > 0 \\ -x, & x \le 0 \end{cases}"
        )
        assert got == "{x^2, x > 0; - x, x <= 0:}"

    def test_trailing_row_break_does_not_leave_an_empty_row(self):
        got = convert(r"\begin{pmatrix} a & b \\ c & d \\ \end{pmatrix}")
        assert got == "(a, b; c, d)"


class TestAligned:
    def test_two_rows(self):
        got = convert(r"\begin{aligned} a &= b + c \\ &= d \end{aligned}")
        assert got == "a & = b + c\n\n& = d"

    def test_gathered(self):
        got = convert(r"\begin{gathered} a = b \\ c = d \end{gathered}")
        assert got == "a = b\n\nc = d"

    def test_top_level_double_backslash_behaves_like_aligned(self):
        # LLMs sometimes emit bare `\\` inside $$...$$ without an explicit
        # environment; SPEC.md 2.2 makes this well-defined regardless.
        got = convert(r"a = b \\ c = d")
        assert got == "a = b\n\nc = d"

    def test_single_newline_break_config(self):
        got = convert(
            r"\begin{aligned} a &= b \\ c &= d \end{aligned}",
            Config(single_newline_break=True),
        )
        assert got == "a & = b\nc & = d"

    def test_no_row_break_is_unaffected(self):
        assert convert(r"a &= b") == "a & = b"


class TestEscapeHatchAndErrors:
    def test_unknown_bare_macro_falls_back_to_tex(self):
        # \digamma has no AsciiMath2 mapping but is a bare symbol with no
        # arguments, so it's safe to embed verbatim via tex(...).
        assert convert(r"\digamma") == "tex(\\digamma)"

    def test_unknown_macro_with_arguments_raises(self):
        with pytest.raises(UnsupportedLatexError):
            convert(r"\widget{x}{y}")

    def test_unsupported_environment_raises(self):
        with pytest.raises(UnsupportedLatexError):
            convert(r"\begin{tikzpicture}\end{tikzpicture}")

    def test_error_names_the_construct(self):
        with pytest.raises(UnsupportedLatexError, match="widget"):
            convert(r"\widget{x}{y}")


class TestUnbracedSingleTokenArguments:
    """`\\mathcal B`, `\\sqrt x`, `\\vec\\imath`, ... - a macro argument with
    no braces around it. Extremely common (especially from LLMs, which
    often skip braces on a single-character argument), and structurally
    different from a braced argument: pylatexenc hands back the bare token
    itself (a LatexCharsNode, or even a nested LatexMacroNode) instead of a
    LatexGroupNode with a `.nodelist`. Regression coverage for a real
    conversion failure this caused (\\mathcal B(X)=\\sigma(\\mathcal T) raised
    AttributeError instead of converting)."""

    def test_font_macro_without_braces(self):
        assert convert(r"\mathcal B") == "cc(B)"

    def test_sqrt_without_braces(self):
        assert convert(r"\sqrt x") == "sqrt(x)"

    def test_accent_without_braces(self):
        assert convert(r"\vec x") == "vec(x)"

    def test_accent_of_a_macro_without_braces(self):
        # the argument itself is another macro, not a plain letter
        assert convert(r"\vec\imath") == "vec(tex(\\imath))"

    def test_originally_reported_expression(self):
        got = convert(r"\mathcal B(X)=\sigma(\mathcal T)")
        assert got == "cc(B) ( X ) = sigma ( cc(T) )"


class TestSizingCommandsAreDropped:
    """\\bigl(/\\bigr) etc. only make sense glued to a delimiter that follows
    them; AsciiMath2's own parens always auto-size via \\left/\\right, so
    keeping the sizing command would leave it stranded (invalid LaTeX)."""

    def test_bigl_bigr_dropped(self):
        got = convert(r"\sigma\bigl(\{a\}\bigr)")
        assert got == "sigma ( { a } )"
        assert "bigl" not in got and "bigr" not in got


class TestRestrictionBar:
    """LaTeX's `\\big|_{X}` ("restricted to X") reaches the renderer as a
    lone "|" character token (`\\big` itself is dropped - see
    TestSizingCommandsAreDropped) immediately followed by a subscript.
    asciimath-parser's own grammar doesn't accept a `_(...)` directly on a
    bare "|" (verified against the published package: the subscript is
    silently dropped, rendering as an unrelated bare group right after
    instead of attaching) - "mid" is the same vertical bar visually and
    *does* parse as a normal scriptable atom, so it's substituted only in
    this exact position. A "|" used anywhere else (absolute value, matrix
    column separator, ...) is untouched."""

    def test_big_pipe_subscript_becomes_mid(self):
        assert convert(r"f\big|_{A}") == "f mid_A"

    def test_plain_pipe_is_untouched_without_a_following_script(self):
        assert convert(r"\left| x \right|") == "|x|"

    def test_originally_reported_expression(self):
        # The exact expression that surfaced both this bug and the "+"/"-"
        # superscript one above: without either fix this converts to
        # "Sigma_(n + 1)^+ |_(C l_n) ~= ..." - the "+" superscript silently
        # swallows the restriction bar into itself, and even once separated
        # the bare "|_(...)" still fails to carry its own subscript.
        got = convert(
            r"\Sigma_{n+1}^{+}\big|_{Cl_n} \cong \Sigma_n \cong \Sigma_{n+1}^{-}\big|_{Cl_n}."
        )
        assert got == (
            "Sigma_(n + 1)^(+) mid_(C l_n) ~= Sigma_n ~= Sigma_(n + 1)^(-) mid_(C l_n) ."
        )


class TestConfig:
    def test_default_config(self):
        cfg = Config()
        assert cfg.multiline_env == "aligned"
        assert cfg.single_newline_break is False
        assert cfg.bar_as_mid is True
        assert cfg.row_break == "\n\n"

    def test_row_break_property(self):
        assert Config(single_newline_break=True).row_break == "\n"


class TestCustomSymbols:
    def test_custom_macro_fills_a_gap(self):
        cfg = Config(custom_macros={"sqcup": "suu"})
        assert convert(r"a \sqcup b", cfg) == "a suu b"

    def test_custom_macro_does_not_override_a_known_macro(self):
        # "le" is already CONST_MACROS-driven; a custom_macros entry for it
        # is simply never consulted (built-in tables win over gap-filling).
        cfg = Config(custom_macros={"le": "should-not-appear"})
        assert convert(r"\le", cfg) == "<="

    def test_custom_text_overrides_default_text_quoting(self):
        cfg = Config(custom_text={"pmf": "pmf"})
        assert convert(r"\text{pmf}", cfg) == "pmf"
        assert convert(r"\text{unmapped}", cfg) == '"unmapped"'

    def test_custom_text_applies_to_operatorname_too(self):
        cfg = Config(custom_text={"LIM": "LIM"})
        assert convert(r"\operatorname*{LIM}", cfg) == "LIM"
        assert convert(r"\operatorname{arg}") == "op(arg)"
