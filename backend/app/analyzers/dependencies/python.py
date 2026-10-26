import re
import tomllib
from typing import Optional

import structlog

from app.analyzers.dependencies.base import BaseDependencyParser, DependencyMetadata

logger = structlog.get_logger(__name__)

# Matches package identifier, optional extras in brackets, and optional version specifier
_REQ_PATTERN = re.compile(r"^([a-zA-Z0-9_\-\.]+)(?:\[[^\]]*\])?\s*([=><~!@].*)?$")


def _clean_req_version(raw_spec: Optional[str]) -> str:
    """Normalizes raw requirement version specifier or defaults to wildcard."""
    if not raw_spec:
        return "*"
    clean = raw_spec.strip()
    if clean.startswith("==") and not any(op in clean[2:] for op in ("<", ">", ",", "!")):
        return clean[2:].strip()
    return clean


def parse_requirements_txt(
    content: str,
    file_path: str = "requirements.txt",
) -> list[DependencyMetadata]:
    """Parses Python requirements.txt file into structured DependencyMetadata records."""
    dependencies: list[DependencyMetadata] = []
    is_dev_file = any(token in file_path.lower() for token in ("dev", "test", "lint", "ci"))

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        # Strip inline comments and environment markers
        line = line.split("#", 1)[0].strip()
        line = line.split(";", 1)[0].strip()
        if not line:
            continue
        # Ignore pip execution directives (-r, -i, --index-url, etc.)
        if line.startswith(("-", "--")):
            continue

        match = _REQ_PATTERN.match(line)
        if match:
            pkg_name = match.group(1).strip().lower()
            ver_spec = _clean_req_version(match.group(2))
            dependencies.append(
                DependencyMetadata(
                    name=pkg_name,
                    version=ver_spec,
                    source_file=file_path,
                    is_dev=is_dev_file,
                )
            )

    logger.info(
        "requirements_parsed",
        file_path=file_path,
        count=len(dependencies),
    )
    return dependencies


def parse_pyproject_toml(
    content: str,
    file_path: str = "pyproject.toml",
) -> list[DependencyMetadata]:
    """Parses PEP 621 and Poetry dependency declarations from pyproject.toml."""
    dependencies: list[DependencyMetadata] = []
    try:
        data = tomllib.loads(content)
    except Exception as exc:
        logger.error("pyproject_toml_parse_failed", file_path=file_path, error=str(exc))
        return []

    # 1. PEP 621: [project.dependencies] (runtime)
    project_deps = data.get("project", {}).get("dependencies", [])
    if isinstance(project_deps, list):
        for dep_str in project_deps:
            if isinstance(dep_str, str):
                match = _REQ_PATTERN.match(dep_str.split(";", 1)[0].strip())
                if match:
                    dependencies.append(
                        DependencyMetadata(
                            name=match.group(1).strip().lower(),
                            version=_clean_req_version(match.group(2)),
                            source_file=file_path,
                            is_dev=False,
                        )
                    )

    # 2. PEP 621: [project.optional-dependencies] (dev / test)
    opt_deps = data.get("project", {}).get("optional-dependencies", {})
    if isinstance(opt_deps, dict):
        for _, group_deps in opt_deps.items():
            if isinstance(group_deps, list):
                for dep_str in group_deps:
                    if isinstance(dep_str, str):
                        match = _REQ_PATTERN.match(dep_str.split(";", 1)[0].strip())
                        if match:
                            dependencies.append(
                                DependencyMetadata(
                                    name=match.group(1).strip().lower(),
                                    version=_clean_req_version(match.group(2)),
                                    source_file=file_path,
                                    is_dev=True,
                                )
                            )

    # 3. Poetry: [tool.poetry.dependencies]
    poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
    if isinstance(poetry_deps, dict):
        for name, spec in poetry_deps.items():
            if name.lower() == "python":
                continue
            is_dev = False
            version = "*"
            if isinstance(spec, str):
                version = spec.strip()
            elif isinstance(spec, dict):
                version = str(spec.get("version", "*")).strip()
                is_dev = bool(spec.get("optional", False) or spec.get("dev", False))

            dependencies.append(
                DependencyMetadata(
                    name=name.strip().lower(),
                    version=version,
                    source_file=file_path,
                    is_dev=is_dev,
                )
            )

    # 4. Poetry: [tool.poetry.group.<group>.dependencies]
    poetry_groups = data.get("tool", {}).get("poetry", {}).get("group", {})
    if isinstance(poetry_groups, dict):
        for _, group_data in poetry_groups.items():
            g_deps = group_data.get("dependencies", {})
            if isinstance(g_deps, dict):
                for name, spec in g_deps.items():
                    if name.lower() == "python":
                        continue
                    if isinstance(spec, str):
                        version = spec.strip()
                    else:
                        version = str(spec.get("version", "*")).strip()
                    dependencies.append(
                        DependencyMetadata(
                            name=name.strip().lower(),
                            version=version,
                            source_file=file_path,
                            is_dev=True,
                        )
                    )

    logger.info("pyproject_parsed", file_path=file_path, count=len(dependencies))
    return dependencies


class PythonDependencyParser(BaseDependencyParser):
    """Dispatcher parser for Python package dependency manifests."""

    def parse(self, content_str: str, file_path: str) -> list[DependencyMetadata]:
        """Dispatches to requirements or pyproject parser based on file path."""
        if file_path.lower().endswith(".toml"):
            return parse_pyproject_toml(content_str, file_path=file_path)
        return parse_requirements_txt(content_str, file_path=file_path)
