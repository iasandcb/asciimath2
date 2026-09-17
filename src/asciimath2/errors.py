class UnsupportedLatexError(Exception):
    """Raised when a LaTeX construct has no known AsciiMath2 rendering.

    Carries the offending macro/environment name so callers can decide
    whether to degrade the whole expression to raw LaTeX (the safe default)
    or report it.
    """

    def __init__(self, what: str, detail: str = ""):
        self.what = what
        self.detail = detail
        message = f"unsupported LaTeX construct: {what}"
        if detail:
            message += f" ({detail})"
        super().__init__(message)
