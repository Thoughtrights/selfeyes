"""Base types shared by all photo sources."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class CandidateRecord:
    id: str                        # globally unique, e.g. "flickr-12345", "loc-cph-3c11432"
    source: str                    # "flickr" | "loc" | "smithsonian"
    original_url: str              # direct URL to full-resolution image
    source_page_url: str           # human-readable source page
    photographer: str
    license_name: str
    license_url: str
    width_px: int
    height_px: int
    tags: list[str] = field(default_factory=list)
    date_taken: str | None = None
    description: str = ""


class Source(ABC):
    """Abstract base for a photo discovery source."""

    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg

    @abstractmethod
    def discover(self) -> Iterator[CandidateRecord]:
        """Yield CandidateRecord objects for each discovered photo."""
        ...
