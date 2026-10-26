from typing import Optional, Sequence

import structlog
import tree_sitter_python as tspython
from tree_sitter import Language, Node, Parser

from app.analyzers.ast.base import BaseASTParser, SymbolMetadata

logger = structlog.get_logger(__name__)


def _clean_docstring(text: str) -> str:
    """Strips enclosing quote tokens and normalizes whitespace from docstrings."""
    cleaned = text.strip()
    if cleaned.startswith(('"""', "'''")):
        cleaned = cleaned[3:-3]
    elif cleaned.startswith(('"', "'")):
        cleaned = cleaned[1:-1]
    return cleaned.strip()


def _get_docstring(body_node: Optional[Node], code_bytes: bytes) -> Optional[str]:
    """Extracts leading string literal from a block body if present as a docstring."""
    if not body_node:
        return None

    for child in body_node.children:
        if child.type == "expression_statement":
            for grand in child.children:
                if grand.type == "string":
                    raw = code_bytes[grand.start_byte:grand.end_byte].decode(
                        "utf-8", errors="replace"
                    )
                    return _clean_docstring(raw)
            break
        elif child.type not in ("comment", "\n"):
            break
    return None


def _parse_function_definition(
    node: Node,
    code_bytes: bytes,
    in_class: bool = False,
    decorators: Optional[Sequence[str]] = None,
) -> SymbolMetadata:
    """Extracts function, async function, or method SymbolMetadata from an AST node."""
    name_node = node.child_by_field_name("name")
    params_node = node.child_by_field_name("parameters")
    return_node = node.child_by_field_name("return_type")
    body_node = node.child_by_field_name("body")

    name = (
        code_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
        if name_node
        else "anonymous"
    )
    params = (
        code_bytes[params_node.start_byte:params_node.end_byte].decode("utf-8", errors="replace")
        if params_node
        else "()"
    )
    if return_node:
        ret_str = code_bytes[return_node.start_byte:return_node.end_byte].decode(
            "utf-8", errors="replace"
        )
        ret = f" -> {ret_str}"
    else:
        ret = ""

    is_async = any(c.type == "async" for c in node.children)
    if in_class:
        sym_type = "method"
    elif is_async:
        sym_type = "async_function"
    else:
        sym_type = "function"

    prefix = "async def " if is_async else "def "
    sig = f"{prefix}{name}{params}{ret}"
    doc = _get_docstring(body_node, code_bytes)

    # If wrapped in decorated_definition, start line begins at highest decorator
    if node.parent and node.parent.type == "decorated_definition":
        start_line = node.parent.start_point.row + 1
    else:
        start_line = node.start_point.row + 1

    end_line = node.end_point.row + 1

    return SymbolMetadata(
        name=name,
        symbol_type=sym_type,
        start_line=start_line,
        end_line=end_line,
        signature=sig,
        docstring=doc,
        decorators=list(decorators) if decorators else [],
    )


def _parse_class_definition(
    node: Node,
    code_bytes: bytes,
    decorators: Optional[Sequence[str]] = None,
) -> list[SymbolMetadata]:
    """Extracts class definition and recursively catalogs internal methods."""
    name_node = node.child_by_field_name("name")
    superclasses_node = node.child_by_field_name("superclasses")
    body_node = node.child_by_field_name("body")

    name = (
        code_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
        if name_node
        else "anonymous"
    )
    bases = (
        code_bytes[superclasses_node.start_byte:superclasses_node.end_byte].decode(
            "utf-8", errors="replace"
        )
        if superclasses_node
        else ""
    )
    sig = f"class {name}{bases}"
    doc = _get_docstring(body_node, code_bytes)

    if node.parent and node.parent.type == "decorated_definition":
        start_line = node.parent.start_point.row + 1
    else:
        start_line = node.start_point.row + 1

    end_line = node.end_point.row + 1

    class_symbol = SymbolMetadata(
        name=name,
        symbol_type="class",
        start_line=start_line,
        end_line=end_line,
        signature=sig,
        docstring=doc,
        decorators=list(decorators) if decorators else [],
    )

    symbols = [class_symbol]
    if body_node:
        symbols.extend(_walk_symbols(body_node, code_bytes, in_class=True))
    return symbols


def _walk_symbols(
    node: Node,
    code_bytes: bytes,
    in_class: bool = False,
) -> list[SymbolMetadata]:
    """Walks the AST node children to extract functions, classes, and decorated definitions."""
    symbols: list[SymbolMetadata] = []

    for child in node.children:
        if child.type == "decorated_definition":
            decs: list[str] = []
            target_def: Optional[Node] = None

            for sub in child.children:
                if sub.type == "decorator":
                    raw_dec = code_bytes[sub.start_byte:sub.end_byte].decode(
                        "utf-8", errors="replace"
                    ).strip()
                    decs.append(raw_dec)
                elif sub.type in ("function_definition", "class_definition"):
                    target_def = sub

            if target_def:
                if target_def.type == "function_definition":
                    symbols.append(
                        _parse_function_definition(
                            target_def, code_bytes, in_class=in_class, decorators=decs
                        )
                    )
                elif target_def.type == "class_definition":
                    symbols.extend(
                        _parse_class_definition(target_def, code_bytes, decorators=decs)
                    )

        elif child.type == "function_definition":
            symbols.append(_parse_function_definition(child, code_bytes, in_class=in_class))

        elif child.type == "class_definition":
            symbols.extend(_parse_class_definition(child, code_bytes))

    return symbols


class PythonASTParser(BaseASTParser):
    """Deterministic AST parser for Python source code powered by Tree-sitter."""

    def __init__(self) -> None:
        self.language = Language(tspython.language())
        self.parser = Parser(self.language)

    def parse(self, code_bytes: bytes) -> list[SymbolMetadata]:
        """Parses Python source bytes into deterministic SymbolMetadata instances."""
        try:
            tree = self.parser.parse(code_bytes)
            symbols = _walk_symbols(tree.root_node, code_bytes, in_class=False)
            symbols.sort(key=lambda s: s.start_line)
            logger.info("python_ast_parsed", symbol_count=len(symbols))
            return symbols
        except Exception as exc:
            logger.error("python_ast_parse_failed", error=str(exc))
            return []
