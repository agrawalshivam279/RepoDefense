from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class DependencyMetadata(BaseModel):
    """Deterministic structural metadata extracted for a third-party dependency."""

    name: str = Field(description="Normalized package identifier name")
    version: str = Field(
        default="*",
        description="Version string or semver constraint (e.g. '>=1.0.0', '2.8.0')",
    )
    source_file: str = Field(
        description="Relative manifest file path (e.g. 'requirements.txt', 'package.json')",
    )
    is_dev: bool = Field(
        default=False,
        description="Flag indicating whether this is a development or test dependency",
    )


class BaseDependencyParser(ABC):
    """Abstract base class for language manifest dependency parsers."""

    @abstractmethod
    def parse(self, content_str: str, file_path: str) -> list[DependencyMetadata]:
        """Parses manifest content into a list of DependencyMetadata instances.

        Args:
            content_str: UTF-8 source string of the dependency manifest.
            file_path: Relative filesystem path to the manifest file.

        Returns:
            List of DependencyMetadata schemas.
        """
        raise NotImplementedError
