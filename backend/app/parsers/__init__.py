# Importing a parser module registers its parsers.
from app.parsers import chase  # noqa: F401
from app.parsers.base import REGISTRY, ParseError, detect_parser  # noqa: F401
