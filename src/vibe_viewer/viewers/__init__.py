"""Built-in viewer widgets."""

from vibe_viewer.core.registry import ViewerRegistry
from vibe_viewer.viewers.archive import ArchiveViewer
from vibe_viewer.viewers.binary import BinaryViewer
from vibe_viewer.viewers.data import DataViewer
from vibe_viewer.viewers.document import DocumentViewer
from vibe_viewer.viewers.email_contacts import MessageAndContactViewer
from vibe_viewer.viewers.font import FontViewer
from vibe_viewer.viewers.image import ImageViewer
from vibe_viewer.viewers.media import MediaViewer
from vibe_viewer.viewers.office import OfficeDocumentViewer
from vibe_viewer.viewers.special_text import GeoDataViewer, PlaylistViewer, SubtitleViewer
from vibe_viewer.viewers.spreadsheet import DelimitedTableViewer, SpreadsheetViewer
from vibe_viewer.viewers.technical import (
    BinaryStructureViewer,
    CaptureViewer,
    ModelViewer,
    PackageMetadataViewer,
)
from vibe_viewer.viewers.text import StructuredTextViewer, TextViewer


def register_default_viewers(registry: ViewerRegistry) -> None:
    """Register all viewers in priority order."""
    for viewer_class in (
        SpreadsheetViewer,
        DelimitedTableViewer,
        PackageMetadataViewer,
        ImageViewer,
        DocumentViewer,
        OfficeDocumentViewer,
        MediaViewer,
        ArchiveViewer,
        GeoDataViewer,
        SubtitleViewer,
        PlaylistViewer,
        ModelViewer,
        DataViewer,
        BinaryStructureViewer,
        CaptureViewer,
        MessageAndContactViewer,
        FontViewer,
        StructuredTextViewer,
        TextViewer,
        BinaryViewer,
    ):
        registry.register(viewer_class)


__all__ = ["register_default_viewers"]
