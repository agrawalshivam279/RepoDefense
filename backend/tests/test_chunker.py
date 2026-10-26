import uuid

from app.analyzers.chunker import chunk_analyzed_file, estimate_token_count
from app.models.analysis import CodeSymbol
from app.schemas.chunk import ChunkType, CodeChunk


def test_estimate_token_count():
    """Verifies deterministic character-to-token count approximations."""
    assert estimate_token_count("") == 1
    assert estimate_token_count("   ") == 1
    assert estimate_token_count("abcd") == 1
    assert estimate_token_count("abcdefghijkl") == 3


def test_chunk_empty_file():
    """Verifies that empty or whitespace-only files return an empty list."""
    file_id = uuid.uuid4()
    assert chunk_analyzed_file(file_id, "empty.py", "", "python", []) == []
    assert chunk_analyzed_file(file_id, "spaces.py", "   \n\n  ", "python", []) == []


def test_chunk_file_without_symbols_fallback():
    """Verifies sliding window fallback for non-symbol files like config or Markdown."""
    file_id = uuid.uuid4()
    content = "\n".join(f"line {i}: content about project setup" for i in range(1, 101))

    chunks = chunk_analyzed_file(
        file_id=file_id,
        file_path="README.md",
        content=content,
        language="markdown",
        symbols=[],
        max_tokens=100,
    )

    assert len(chunks) > 1
    for chunk in chunks:
        assert isinstance(chunk, CodeChunk)
        assert chunk.chunk_type == ChunkType.FALLBACK
        assert chunk.language == "markdown"
        assert chunk.start_line >= 1
        assert chunk.end_line <= 100
        assert chunk.start_line <= chunk.end_line


def test_chunk_file_with_symbols_and_header():
    """Verifies module header isolation and symbol-aligned chunking."""
    file_id = uuid.uuid4()
    sym1_id, sym2_id = uuid.uuid4(), uuid.uuid4()

    content = (
        '"""Module docstring."""\n'
        "import os\n"
        "import sys\n"
        "\n"
        "def helper_func():\n"
        "    return 42\n"
        "\n"
        "def main_func():\n"
        "    return helper_func()\n"
    )

    symbols = [
        CodeSymbol(
            id=sym1_id,
            file_id=file_id,
            name="helper_func",
            symbol_type="function",
            start_line=5,
            end_line=6,
        ),
        CodeSymbol(
            id=sym2_id,
            file_id=file_id,
            name="main_func",
            symbol_type="function",
            start_line=8,
            end_line=9,
        ),
    ]

    chunks = chunk_analyzed_file(
        file_id=file_id,
        file_path="app/utils.py",
        content=content,
        language="python",
        symbols=symbols,
        max_tokens=500,
    )

    assert len(chunks) == 3
    # Header
    assert chunks[0].chunk_type == ChunkType.MODULE_HEADER
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 4
    assert "import sys" in chunks[0].content

    # Symbol 1
    assert chunks[1].chunk_type == ChunkType.SYMBOL
    assert chunks[1].symbol_id == sym1_id
    assert chunks[1].symbol_name == "helper_func"
    assert chunks[1].start_line == 5
    assert chunks[1].end_line == 6

    # Symbol 2
    assert chunks[2].chunk_type == ChunkType.SYMBOL
    assert chunks[2].symbol_id == sym2_id
    assert chunks[2].symbol_name == "main_func"
    assert chunks[2].start_line == 8
    assert chunks[2].end_line == 9


def test_chunk_inter_symbol_gap_and_tail():
    """Verifies that code between symbols and at the end of the file is preserved."""
    file_id = uuid.uuid4()
    sym_id = uuid.uuid4()

    content = (
        "def my_func():\n"
        "    pass\n"
        "\n"
        "# Constant definition\n"
        "GLOBAL_VAR = 'active'\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    my_func()\n"
    )

    symbols = [
        CodeSymbol(
            id=sym_id,
            file_id=file_id,
            name="my_func",
            symbol_type="function",
            start_line=1,
            end_line=2,
        )
    ]

    chunks = chunk_analyzed_file(
        file_id=file_id,
        file_path="script.py",
        content=content,
        language="python",
        symbols=symbols,
        max_tokens=500,
    )

    assert len(chunks) == 2
    assert chunks[0].chunk_type == ChunkType.SYMBOL
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 2

    # Trailing code
    assert chunks[1].chunk_type == ChunkType.BLOCK
    assert chunks[1].start_line == 3
    assert chunks[1].end_line == 8
    assert "GLOBAL_VAR" in chunks[1].content


def test_chunk_oversized_symbol():
    """Verifies that an oversized function exceeding max_tokens is sub-chunked."""
    file_id = uuid.uuid4()
    sym_id = uuid.uuid4()

    lines = ["def huge_function():\n"]
    for i in range(1, 101):
        lines.append(f"    var_{i} = calculate_value({i})\n")
    content = "".join(lines)

    symbols = [
        CodeSymbol(
            id=sym_id,
            file_id=file_id,
            name="huge_function",
            symbol_type="function",
            start_line=1,
            end_line=101,
        )
    ]

    chunks = chunk_analyzed_file(
        file_id=file_id,
        file_path="huge.py",
        content=content,
        language="python",
        symbols=symbols,
        max_tokens=50,  # small threshold forces sub-chunking
    )

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.symbol_id == sym_id
        assert chunk.symbol_name == "huge_function"
        assert chunk.chunk_type == ChunkType.BLOCK
        assert chunk.start_line >= 1
        assert chunk.end_line <= 101


def test_chunk_nested_symbols_deduplication():
    """Verifies that a class that fits within max_tokens does not duplicate child methods."""
    file_id = uuid.uuid4()
    class_id = uuid.uuid4()
    method_id = uuid.uuid4()

    content = (
        "class Calculator:\n"
        "    def add(self, a, b):\n"
        "        return a + b\n"
    )

    symbols = [
        CodeSymbol(
            id=class_id,
            file_id=file_id,
            name="Calculator",
            symbol_type="class",
            start_line=1,
            end_line=3,
        ),
        CodeSymbol(
            id=method_id,
            file_id=file_id,
            name="add",
            symbol_type="function",
            start_line=2,
            end_line=3,
        ),
    ]

    chunks = chunk_analyzed_file(
        file_id=file_id,
        file_path="calc.py",
        content=content,
        language="python",
        symbols=symbols,
        max_tokens=500,
    )

    # Class fits into 500 tokens, so only 1 chunk should be emitted for Calculator
    assert len(chunks) == 1
    assert chunks[0].symbol_id == class_id
    assert chunks[0].symbol_name == "Calculator"
    assert chunks[0].chunk_type == ChunkType.SYMBOL
