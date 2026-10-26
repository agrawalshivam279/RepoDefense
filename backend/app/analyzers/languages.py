from pathlib import Path
from typing import Union

# Mapping of file extensions to canonical programming or markup languages
EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    # Python
    ".py": "Python",
    ".pyw": "Python",
    ".pyi": "Python",
    # TypeScript & JavaScript
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    # Go
    ".go": "Go",
    # Java & Kotlin
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".scala": "Scala",
    # Systems
    ".rs": "Rust",
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hpp": "C++",
    ".hxx": "C++",
    ".cs": "C#",
    # Scripting & Web
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".sql": "SQL",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "CSS",
    ".sass": "CSS",
    ".less": "CSS",
    # Data & Configuration
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".md": "Markdown",
    ".markdown": "Markdown",
    ".txt": "Plain Text",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".dockerignore": "Docker",
    ".gitignore": "Git Config",
}

# Special exact filenames mapped to canonical representations
SPECIAL_FILENAMES: dict[str, str] = {
    "dockerfile": "Dockerfile",
    "containerfile": "Dockerfile",
    "makefile": "Makefile",
    "gnumakefile": "Makefile",
    "gemfile": "Ruby",
    "procfile": "Procfile",
    "cmakelists.txt": "CMake",
}


def detect_language(file_path: Union[Path, str]) -> str:
    """Determines the canonical programming language for a given file.

    Evaluates special filenames first, then matches against known file extensions.
    Defaults to 'Plain Text' if no specific language match is found.
    """
    path = Path(file_path) if isinstance(file_path, str) else file_path
    name_lower = path.name.lower()

    if name_lower in SPECIAL_FILENAMES:
        return SPECIAL_FILENAMES[name_lower]

    ext = path.suffix.lower()
    return EXTENSION_LANGUAGE_MAP.get(ext, "Plain Text")
