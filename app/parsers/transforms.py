import re
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from typing import Any

from ..utils.enums import Severity, TransformErrorCode


class TransformError(Exception):
    def __init__(self, code: TransformErrorCode, severity: Severity, message: str):
        self.code = code
        self.severity = severity
        self.message = message
        super().__init__(message)


def strip(v: Any) -> Any:
    return v.strip() if isinstance(v, str) else v


def lower(v: Any) -> Any:
    return v.lower() if isinstance(v, str) else v


def upper(v: Any) -> Any:
    return v.upper() if isinstance(v, str) else v


def title(v: Any) -> Any:
    return v.title() if isinstance(v, str) else v


_NON_ALNUM_RE = re.compile(r"[^0-9A-Za-zА-Яа-яЁё]")


def remove_non_alnum(v: Any) -> Any:
    return _NON_ALNUM_RE.sub("", v) if isinstance(v, str) else v


_THOUSANDS_SPACE_RE = re.compile(r"(?<=\d)[  ](?=\d)")


def strip_thousands_space(v: Any) -> Any:
    return _THOUSANDS_SPACE_RE.sub("", v) if isinstance(v, str) else v


def comma_to_dot(v: Any) -> Any:
    return v.replace(",", ".") if isinstance(v, str) else v


def to_decimal(v: Any) -> Decimal:
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (int, float)):
        return Decimal(str(v))
    if isinstance(v, str):
        try:
            return Decimal(v.strip())
        except InvalidOperation:
            pass
    raise TransformError(
        TransformErrorCode.PRICE_NOT_NUMERIC,
        Severity.ERROR,
        f"cannot convert to decimal: {v!r}",
    )


_EAN13_RE = re.compile(r"^\d{13}$")


def validate_ean13(v: Any) -> str:
    s = str(v).strip() if v is not None else ""
    if not _EAN13_RE.match(s):
        raise TransformError(
            TransformErrorCode.INVALID_BARCODE,
            Severity.WARNING,
            f"not a valid EAN-13: {v!r}",
        )
    digits = [int(c) for c in s]
    checksum = sum(d if i % 2 == 0 else d * 3 for i, d in enumerate(digits[:-1]))
    check_digit = (10 - checksum % 10) % 10
    if check_digit != digits[-1]:
        raise TransformError(
            TransformErrorCode.INVALID_BARCODE,
            Severity.WARNING,
            f"invalid EAN-13 checksum: {v!r}",
        )
    return s


_STOCK_THRESHOLD_RE = re.compile(r"^[<>]\s*(\d+)$")


def stock_from_text(v: Any) -> int:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return int(v)
    if isinstance(v, str):
        s = v.strip()
        if match := _STOCK_THRESHOLD_RE.match(s):
            return int(match.group(1))
        if s.isdigit():
            return int(s)
    raise TransformError(
        TransformErrorCode.STOCK_NOT_PARSEABLE,
        Severity.ERROR,
        f"cannot parse stock value: {v!r}",
    )


def cell_as_text(v: Any) -> Any:
    if v is None:
        return v
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


TRANSFORMS: dict[str, Callable[[Any], Any]] = {
    "strip": strip,
    "lower": lower,
    "upper": upper,
    "title": title,
    "remove_non_alnum": remove_non_alnum,
    "strip_thousands_space": strip_thousands_space,
    "comma_to_dot": comma_to_dot,
    "to_decimal": to_decimal,
    "validate_ean13": validate_ean13,
    "stock_from_text": stock_from_text,
    "cell_as_text": cell_as_text,
}
