"""What the renderer reads AsciiMath2 text as - so the converter can tell
when two pieces of output may be written side by side without a space.

asciimath-parser (the renderer, see SPEC.md) tokenizes greedily, with no
backtracking: from each position it follows its symbol trie as far as the
text allows and takes whatever it walked as one token. So "x" next to "x"
reads as `xx` (\\times), "p" next to "i" as `pi`, "c" next to "c" as `cc`
(\\mathcal) - while "a" next to "b" stays two letters. `tokenize` is a port
of that tokenizer (`tryParsingAll` in its dist/index.js), and `same_reading`
asks whether joining two pieces changes how they're read.
"""

# Every key of asciimath-parser 0.6.11's SYMBOLMAP, plus the six its
# AsciiMath class adds by default (dx, dy, dz, dt, #, atop) - the tokens the
# renderer knows before any caller-supplied symbols.
RENDERER_TOKENS: tuple[str, ...] = (
    'alpha', 'beta', 'gamma', 'Gamma', 'delta', 'Delta', 'epsi', 'epsilon',
    'varepsilon', 'zeta', 'eta', 'theta', 'Theta', 'vartheta', 'iota', 'kappa',
    'lambda', 'Lambda', 'mu', 'nu', 'xi', 'Xi', 'pi', 'Pi', 'rho', 'sigma', 'Sigma',
    'tau', 'upsilon', 'phi', 'varphi', 'varPhi', 'phv', 'Phv', 'Phi', 'chi', 'psi',
    'Psi', 'omega', 'Omega', '***', 'star', '**', 'ast', '*', 'cdot', '//', '\\\\',
    'setminus', 'xx', '|><', '><|', '|><|', '-:', '@', 'o+', 'ox', 'o.', 'sum', 'prod',
    '^^', '^^^', 'vv', 'vvv', 'nn', 'nnn', 'uu', 'uuu', '!=', 'lt', '<<', '>>', '<=',
    'le', 'gt', '>=', 'ge', '-<', '>-', '-<=', '>-=', 'in', '!in', 'sub', 'sup',
    'sube', 'supe', '-=', '~=', '~', '~~', '\\#', '\\&', '\\@', '\\%', '%', '\\_',
    '\\^', '\\$', '\\ ', '\\,', '\\;', '\\:', '\\!', 'enspace', 'hspace', 'prop',
    'comp', 'complement', ':=', '=:', 'if', 'otherwise', 'and', 'or', 'not', '=>',
    '=/=>', '~>', '-/->', '<-/-', '<-/->', '<==', '<=>', '<=/=>', 'iff', '!iff', 'AA',
    'EE', '_|_', 'TT', '|--', '|==', 'int', 'oint', 'del', 'grad', '+-', '-+', 'O/',
    'oo', 'aleph', '...', ':.', ":'", '/_', '/_\\', 'quad', 'qquad', 'cdots', 'vdots',
    'ddots', 'diamond', 'Lap', 'square', '|__', '__|', '|~', '~|', 'CC', 'NN', 'QQ',
    'RR', 'ZZ', "'", "''", "'''", 'lim', 'sin', 'cos', 'tan', 'sinh', 'cosh', 'tanh',
    'cot', 'sec', 'csc', 'arcsin', 'arccos', 'arctan', 'coth', 'sech', 'csch', 'exp',
    'log', 'ln', 'det', 'dim', 'gcd', 'lcm', 'min', 'max', 'Sup', 'inf', 'mod', 'sgn',
    'arg', 'Arg', 'abs', 'norm', 'floor', 'ceil', 'uarr', 'uparrow', 'darr',
    'downarrow', 'rarr', 'rightarrow', 'to', '->', '<-', '>->', '->>', '>->>', '|->',
    'larr', 'leftarrow', 'harr', 'rArr', 'lArr', 'hArr', 'curvArrLt', 'curvArrRt',
    'circArrLt', 'circArrRt', 'sqrt', 'root', 'frac', '/', 'choose', '_', '^',
    'stackrel', 'overset', 'underset', 'hat', '\\`', 'widehat', 'Hat', 'widetilde',
    'ol', 'overline', 'arc', 'bar', 'vec', 'Vec', 'Aec', 'tilde', 'Tilde', 'dot',
    'ddot', 'ul', 'underline', 'underbrace', 'ubrace', 'overbrace', 'obrace', 'color',
    'phantom', 'text', 'tex', 'mbox', 'op', 'cancel', 'bb', 'mathbf', 'sf', 'mathsf',
    'bbb', 'mathbb', 'cc', 'mathcal', 'tt', 'mathtt', 'fr', 'bm', 'rm', 'scr',
    'limits', 'iint', 'iiint', 'oiint', 'oiiint', 'laplace', '==', '-->', '||', '!||',
    'S=', 'S~', '!-=', '!|', '!', '!!', '!sube', '!supe', 'subne', 'supne', 'lhd',
    'rhd', 'normal', 'rnormal', 'hline', '--', '(', ')', '[', ']', '{', '}', '(:',
    ':)', '{:', ':}', '|', 'mid', '&', '&&', ',', ';', '-', '+', 'part', 'pp', 'dd',
    'tiny', 'small', 'large', 'huge', 'o1', 'o2', 'o3', 'o4', 'o5', 'o6', 'ce', 'Ksp',
    'Ka1', 'Ka2', 'Ka3', 'Ka', 'Kb', 'Kh1', 'Kh2', 'Kh3', 'Kh', 'Kw', 'pH', 'pOH',
    'cyc', 'dx', 'dy', 'dz', 'dt', '#', 'atop',
)


class _Trie:
    def __init__(self, tokens) -> None:
        self.root: dict = {}
        for token in tokens:
            node = self.root
            for ch in token:
                node = node.setdefault(ch, {})
            node[""] = True  # end of a token


def _trie(extra: frozenset[str]) -> _Trie:
    key = extra
    cached = _TRIES.get(key)
    if cached is None:
        cached = _TRIES[key] = _Trie(RENDERER_TOKENS + tuple(sorted(extra)))
    return cached


_TRIES: dict[frozenset[str], _Trie] = {}


def tokenize(text: str, extra: frozenset[str] = frozenset()) -> list[tuple[str, str]]:
    """`text` as the renderer reads it: ("K", symbol) for each symbol, and
    ("C", ch) for each character of anything else - a run of letters that
    isn't a symbol renders as those letters whichever way it was split, so
    only symbols are worth telling apart."""
    root = _trie(extra).root
    out: list[tuple[str, str]] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        node, j = root, i
        while j < n and text[j] in node:
            node = node[text[j]]
            j += 1
        if j > i:
            if node.get(""):
                out.append(("K", text[i:j]))
            else:
                out.extend(("C", c) for c in text[i:j])
            i = j
            continue
        if ch == '"':
            end = text.find('"', i + 1)
            end = n if end == -1 else end + 1
            out.extend(("C", c) for c in text[i:end])
            i = end
            continue
        # A number, or a run of characters none of which starts a symbol.
        j = i
        while j < n and not text[j].isspace() and (j == i or text[j] not in root):
            j += 1
        out.extend(("C", c) for c in text[i:j])
        i = j
    return out


def same_reading(left: str, right: str, extra: frozenset[str] = frozenset()) -> bool:
    """Whether `left` and `right` written with no space between them read as
    the same symbols as with one."""
    return tokenize(left + right, extra) == tokenize(left, extra) + tokenize(right, extra)
