from typing import Optional, Sequence

import structlog
import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Node, Parser

from app.analyzers.ast.base import BaseASTParser, SymbolMetadata

logger = structlog.get_logger(__name__)


def _node_text(node: Optional[Node], code_bytes: bytes) -> str:
    """Decodes AST node byte range into UTF-8 text safely."""
    if not node:
        return ""
    return code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _clean_jsdoc(text: str) -> str:
    """Normalizes JSDoc / block comment delimiters into clean text."""
    cleaned = text.strip()
    if cleaned.startswith("/**") and cleaned.endswith("*/"):
        cleaned = cleaned[3:-2].strip()
    elif cleaned.startswith("/*") and cleaned.endswith("*/"):
        cleaned = cleaned[2:-2].strip()

    raw_lines: list[str] = []
    for line in cleaned.splitlines():
        line = line.strip()
        if line.startswith("*"):
            line = line[1:].strip()
        raw_lines.append(line)

    while raw_lines and not raw_lines[0]:
        raw_lines.pop(0)
    while raw_lines and not raw_lines[-1]:
        raw_lines.pop()

    return "\n".join(raw_lines).strip()


def _extract_docstring(
    pending_comment: Optional[Node],
    statement_start: int,
    code_bytes: bytes,
) -> Optional[str]:
    """Extracts and cleans leading JSDoc comment if adjacent to statement start."""
    if not pending_comment:
        return None
    if statement_start - (pending_comment.end_point.row + 1) <= 2:
        raw = _node_text(pending_comment, code_bytes)
        if raw.startswith("/*"):
            return _clean_jsdoc(raw)
    return None


def _parse_method_definition(
    node: Node,
    code_bytes: bytes,
    decorators: Sequence[str],
    docstring: Optional[str],
    start_line: int,
) -> SymbolMetadata:
    """Extracts method SymbolMetadata from a class body method_definition node."""
    name_node = node.child_by_field_name("name")
    params_node = node.child_by_field_name("parameters")
    ret_node = node.child_by_field_name("return_type")
    is_async = any(c.type == "async" for c in node.children)

    name = _node_text(name_node, code_bytes) or "anonymous"
    params = _node_text(params_node, code_bytes) or "()"
    ret_str = f" {_node_text(ret_node, code_bytes)}" if ret_node else ""
    prefix = "async " if is_async else ""
    sig = f"{prefix}{name}{params}{ret_str}"

    return SymbolMetadata(
        name=name,
        symbol_type="method",
        start_line=start_line,
        end_line=node.end_point.row + 1,
        signature=sig,
        docstring=docstring,
        decorators=list(decorators),
    )


def _parse_class_body(
    body_node: Node,
    code_bytes: bytes,
) -> list[SymbolMetadata]:
    """Walks the children of a class_body node to extract nested methods and docstrings."""
    methods: list[SymbolMetadata] = []
    m_comment: Optional[Node] = None
    m_decs: list[tuple[int, str]] = []

    for child in body_node.children:
        if child.type == "comment":
            m_comment = child
        elif child.type == "decorator":
            m_decs.append((child.start_point.row + 1, _node_text(child, code_bytes).strip()))
        elif child.type == "method_definition":
            dec_start = m_decs[0][0] if m_decs else child.start_point.row + 1
            m_doc = _extract_docstring(m_comment, dec_start, code_bytes)
            m_comment = None

            method_sym = _parse_method_definition(
                child,
                code_bytes,
                decorators=[d[1] for d in m_decs],
                docstring=m_doc,
                start_line=dec_start,
            )
            methods.append(method_sym)
            m_decs = []

    return methods


def _walk_ts_symbols(root_node: Node, code_bytes: bytes) -> list[SymbolMetadata]:
    """Walks top-level AST nodes to extract functions, classes, interfaces, and methods."""
    symbols: list[SymbolMetadata] = []
    pending_comment: Optional[Node] = None
    pending_decs: list[tuple[int, str]] = []

    for child in root_node.children:
        if child.type == "comment":
            pending_comment = child
            continue
        elif child.type == "decorator":
            pending_decs.append((child.start_point.row + 1, _node_text(child, code_bytes).strip()))
            continue

        target = child
        parent_stmt: Optional[Node] = None

        if child.type == "export_statement":
            parent_stmt = child
            for sub in child.children:
                if sub.type == "decorator":
                    pending_decs.append(
                        (sub.start_point.row + 1, _node_text(sub, code_bytes).strip())
                    )
                elif sub.type in (
                    "function_declaration",
                    "class_declaration",
                    "interface_declaration",
                    "lexical_declaration",
                ):
                    target = sub

        outer_node = parent_stmt or target
        statement_start = outer_node.start_point.row + 1
        statement_end = outer_node.end_point.row + 1

        start_line = min(pending_decs[0][0], statement_start) if pending_decs else statement_start
        docstring = _extract_docstring(pending_comment, start_line, code_bytes)
        pending_comment = None
        decs = [d[1] for d in pending_decs]
        pending_decs = []

        if target.type == "function_declaration":
            name_node = target.child_by_field_name("name")
            params_node = target.child_by_field_name("parameters")
            ret_node = target.child_by_field_name("return_type")
            is_async = any(c.type == "async" for c in target.children)

            name = _node_text(name_node, code_bytes) or "anonymous"
            params = _node_text(params_node, code_bytes) or "()"
            ret_str = f" {_node_text(ret_node, code_bytes)}" if ret_node else ""
            prefix = "async function " if is_async else "function "
            symbols.append(
                SymbolMetadata(
                    name=name,
                    symbol_type="async_function" if is_async else "function",
                    start_line=start_line,
                    end_line=statement_end,
                    signature=f"{prefix}{name}{params}{ret_str}",
                    docstring=docstring,
                    decorators=decs,
                )
            )

        elif target.type == "lexical_declaration":
            for decl in target.children:
                if decl.type == "variable_declarator":
                    val_node = decl.child_by_field_name("value")
                    if val_node and val_node.type in ("arrow_function", "function_expression"):
                        name_node = decl.child_by_field_name("name")
                        type_node = decl.child_by_field_name("type")
                        is_async = any(c.type == "async" for c in val_node.children)

                        name = _node_text(name_node, code_bytes) or "anonymous"
                        params_node = val_node.child_by_field_name("parameters")
                        params = _node_text(params_node, code_bytes) or "()"
                        type_str = _node_text(type_node, code_bytes)
                        prefix = "async " if is_async else ""
                        if val_node.type == "arrow_function":
                            sig = f"const {name}{type_str} = {prefix}{params} => ..."
                        else:
                            sig = f"const {name}{type_str} = {prefix}function{params}"

                        symbols.append(
                            SymbolMetadata(
                                name=name,
                                symbol_type="async_function" if is_async else "function",
                                start_line=start_line,
                                end_line=statement_end,
                                signature=sig,
                                docstring=docstring,
                                decorators=decs,
                            )
                        )

        elif target.type == "interface_declaration":
            name_node = target.child_by_field_name("name")
            name = _node_text(name_node, code_bytes) or "anonymous"
            extends_node = next(
                (c for c in target.children if c.type == "extends_type_clause"), None
            )
            ext_str = f" {_node_text(extends_node, code_bytes)}" if extends_node else ""
            symbols.append(
                SymbolMetadata(
                    name=name,
                    symbol_type="interface",
                    start_line=start_line,
                    end_line=statement_end,
                    signature=f"interface {name}{ext_str}",
                    docstring=docstring,
                    decorators=decs,
                )
            )

        elif target.type == "class_declaration":
            name_node = target.child_by_field_name("name")
            name = _node_text(name_node, code_bytes) or "anonymous"
            heritage_node = next((c for c in target.children if c.type == "class_heritage"), None)
            her_str = f" {_node_text(heritage_node, code_bytes)}" if heritage_node else ""
            symbols.append(
                SymbolMetadata(
                    name=name,
                    symbol_type="class",
                    start_line=start_line,
                    end_line=statement_end,
                    signature=f"class {name}{her_str}",
                    docstring=docstring,
                    decorators=decs,
                )
            )
            body_node = target.child_by_field_name("body")
            if body_node:
                symbols.extend(_parse_class_body(body_node, code_bytes))

    return symbols


class TypeScriptASTParser(BaseASTParser):
    """Deterministic AST parser for TypeScript, TSX, and JavaScript source code."""

    def __init__(self) -> None:
        self.language = Language(tstypescript.language_tsx())
        self.parser = Parser(self.language)

    def parse(self, code_bytes: bytes) -> list[SymbolMetadata]:
        """Parses TypeScript/JavaScript source bytes into deterministic SymbolMetadata schemas."""
        try:
            tree = self.parser.parse(code_bytes)
            symbols = _walk_ts_symbols(tree.root_node, code_bytes)
            symbols.sort(key=lambda s: s.start_line)
            logger.info("typescript_ast_parsed", symbol_count=len(symbols))
            return symbols
        except Exception as exc:
            logger.error("typescript_ast_parse_failed", error=str(exc))
            return []
