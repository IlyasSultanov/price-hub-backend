from pathlib import PurePosixPath

from .enums import FeedFormat

_ZIP_SIGNATURES = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
_GZIP_SIGNATURE = b"\x1f\x8b"
_PDF_SIGNATURE = b"%PDF-"
_BOMS = (b"\xef\xbb\xbf", b"\xff\xfe", b"\xfe\xff")


class UnsupportedFeedFormat(ValueError):
    pass


def _strip_bom(header: bytes) -> bytes:
    for bom in _BOMS:
        if header.startswith(bom):
            return header[len(bom) :]
    return header


def sniff_format(header: bytes, filename: str) -> FeedFormat | None:
    """Detect the feed format from the first bytes of the file, cross-checked
    against its extension. Returns None for a .zip/.gz archive whose inner
    format is resolved later, at parse time. Raises UnsupportedFeedFormat when
    the actual bytes don't match what the extension claims."""
    ext = PurePosixPath(filename.lower()).suffix

    if header.startswith(_GZIP_SIGNATURE):
        if ext != ".gz":
            raise UnsupportedFeedFormat(
                f"gzip signature does not match extension {ext!r}"
            )
        return None

    if any(header.startswith(sig) for sig in _ZIP_SIGNATURES):
        if ext == ".xlsx":
            return FeedFormat.XLSX
        if ext == ".zip":
            return None
        raise UnsupportedFeedFormat(f"zip signature does not match extension {ext!r}")

    if header.startswith(_PDF_SIGNATURE):
        if ext != ".pdf":
            raise UnsupportedFeedFormat(
                f"pdf signature does not match extension {ext!r}"
            )
        return FeedFormat.PDF

    stripped = _strip_bom(header).lstrip(b" \t\r\n")
    if stripped.startswith(b"<"):
        if ext != ".xml":
            raise UnsupportedFeedFormat(
                f"xml signature does not match extension {ext!r}"
            )
        return FeedFormat.XML

    if ext == ".csv":
        return FeedFormat.CSV
    if ext == ".tsv":
        return FeedFormat.TSV

    raise UnsupportedFeedFormat(f"unsupported or unrecognized file: {filename!r}")
