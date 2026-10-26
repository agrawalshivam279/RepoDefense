import json

import structlog

from app.analyzers.dependencies.base import BaseDependencyParser, DependencyMetadata

logger = structlog.get_logger(__name__)


def parse_package_json(
    content: str,
    file_path: str = "package.json",
) -> list[DependencyMetadata]:
    """Parses npm/yarn package.json dependencies, devDependencies, and peerDependencies."""
    dependencies: list[DependencyMetadata] = []
    try:
        data = json.loads(content)
    except Exception as exc:
        logger.error("package_json_parse_failed", file_path=file_path, error=str(exc))
        return []

    sections = [
        ("dependencies", False),
        ("devDependencies", True),
        ("peerDependencies", False),
        ("optionalDependencies", False),
    ]

    for section_key, is_dev in sections:
        section_data = data.get(section_key, {})
        if isinstance(section_data, dict):
            for name, version in section_data.items():
                pkg_name = str(name).strip().lower()
                ver_spec = str(version).strip() if version else "*"
                dependencies.append(
                    DependencyMetadata(
                        name=pkg_name,
                        version=ver_spec,
                        source_file=file_path,
                        is_dev=is_dev,
                    )
                )

    logger.info("package_json_parsed", file_path=file_path, count=len(dependencies))
    return dependencies


class NodeDependencyParser(BaseDependencyParser):
    """Deterministic parser for Node.js package manifests."""

    def parse(self, content_str: str, file_path: str) -> list[DependencyMetadata]:
        """Parses package.json content into structured DependencyMetadata schemas."""
        return parse_package_json(content_str, file_path=file_path)
