"""AsciiMath2: LaTeX -> AsciiMath2 conversion.

See SPEC.md (repo root) for the AsciiMath2 standard this implements.
"""

from .config import Config
from .errors import UnsupportedLatexError
from .render import convert

__all__ = ["convert", "Config", "UnsupportedLatexError"]
