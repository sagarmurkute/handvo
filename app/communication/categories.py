"""Communication category and item definitions."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class CommunicationItem:
    """An AAC word or phrase item."""
    item_id: str
    label: str
    text: str
    category_id: str
    accent_color: str = "#38bdf8"
    icon: str = ""
    enabled: bool = True


@dataclass
class CommunicationCategory:
    """A collection of themed communication items."""
    category_id: str
    name: str
    icon: str
    accent_color: str
    items: List[CommunicationItem] = field(default_factory=list)
