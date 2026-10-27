import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from ...parsers.transforms import TRANSFORMS, TransformError
from ...schemas.mapping_profiles import Rules
from ...utils import Currency, Severity

REQUIRED_FIELDS = ("external_sku", "title", "price")

# Allowed mapping-profile fields with no column on `offers` yet (reserved for
# the Этап 4 matching pipeline): mfr_article, description, category_raw,
# old_price, available. Mapping them is harmless; they're just not persisted.
_OFFER_COLUMN_FIELDS = frozenset(
    {"external_sku", "barcode", "brand", "title", "price", "currency", "stock"}
)


def _stringify(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)[:255]


@dataclass
class RowOutcome:
    offer: dict[str, Any] | None
    error_rows: list[dict[str, Any]]


class RowMapper:
    """Maps one raw CSV row to an `offers` insert dict using a mapping
    profile's column_map + transforms, honoring its `rules`.

    A row is one of three outcomes:
      - filtered out silently (service row / matched skip regex): offer=None, error_rows=[]
      - rejected (missing required field, a transform raised Severity.ERROR,
        or a rule says so): offer=None, error_rows=[...]
      - accepted, possibly with soft (Severity.WARNING) field-level errors
        that nulled a field but didn't reject the row: offer={...}, error_rows=[...]
    """

    def __init__(
        self,
        column_map: dict[str, str],
        transforms: dict[str, list[str]],
        rules: Rules,
        default_currency: Currency,
    ):
        self.column_map = column_map
        self.transforms = transforms
        self.rules = rules
        self.default_currency = default_currency
        self._skip_re = (
            re.compile(rules.skip_row_if_title_matches)
            if rules.skip_row_if_title_matches
            else None
        )

    def _is_service_row(self, raw_row: list[str]) -> bool:
        if self.rules.service_row_heuristic != "only_first_column_filled":
            return False
        non_empty = [cell for cell in raw_row if cell and cell.strip()]
        return bool(raw_row) and bool(raw_row[0].strip()) and len(non_empty) == 1

    def _coerce_decimal(
        self, value: Any, field: str, reject: list[dict]
    ) -> Decimal | None:
        if isinstance(value, Decimal):
            return value
        try:
            return TRANSFORMS["to_decimal"](value)
        except TransformError as exc:
            reject.append(
                {"field": field, "code": exc.code.value, "raw_value": _stringify(value)}
            )
            return None

    def _coerce_stock(self, value: Any, reject: list[dict]) -> int | None:
        if value is None:
            return 0
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        mapped = self.rules.stock_text_map.get(str(value).strip())
        if mapped is not None:
            return mapped
        try:
            return TRANSFORMS["stock_from_text"](value)
        except TransformError as exc:
            reject.append(
                {
                    "field": "stock",
                    "code": exc.code.value,
                    "raw_value": _stringify(value),
                }
            )
            return None

    def map_row(self, header_index: dict[str, int], raw_row: list[str]) -> RowOutcome:
        if self._is_service_row(raw_row):
            return RowOutcome(None, [])

        values: dict[str, Any] = {}
        reject: list[dict[str, Any]] = []
        soft: list[dict[str, Any]] = []

        for field, header_name in self.column_map.items():
            if field not in _OFFER_COLUMN_FIELDS:
                continue
            idx = header_index.get(header_name)
            raw_value = raw_row[idx] if idx is not None and idx < len(raw_row) else None
            value = raw_value
            try:
                for transform_name in self.transforms.get(field, []):
                    value = TRANSFORMS[transform_name](value)
                values[field] = value
            except TransformError as exc:
                entry = {
                    "field": field,
                    "code": exc.code.value,
                    "raw_value": _stringify(raw_value),
                }
                if exc.severity == Severity.ERROR:
                    reject.append(entry)
                else:
                    values[field] = None
                    soft.append(entry)

        title_value = values.get("title")
        if (
            self._skip_re is not None
            and title_value
            and self._skip_re.search(str(title_value))
        ):
            return RowOutcome(None, [])

        if "price" in values:
            values["price"] = self._coerce_decimal(values["price"], "price", reject)
        values["stock"] = self._coerce_stock(values.get("stock"), reject)

        for field in REQUIRED_FIELDS:
            value = values.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                reject.append(
                    {
                        "field": field,
                        "code": "missing_required_field",
                        "raw_value": None,
                    }
                )

        if values["stock"] is not None and values["stock"] < 0:
            policy = self.rules.on_negative_stock or "keep"
            if policy == "reject_row":
                reject.append(
                    {
                        "field": "stock",
                        "code": "negative_stock",
                        "raw_value": str(values["stock"]),
                    }
                )
            elif policy == "set_zero":
                values["stock"] = 0

        if reject:
            return RowOutcome(None, reject)

        currency_raw = values.get("currency")
        if currency_raw:
            try:
                currency = Currency(str(currency_raw).strip().upper())
            except ValueError:
                reject.append(
                    {
                        "field": "currency",
                        "code": "invalid_currency",
                        "raw_value": _stringify(currency_raw),
                    }
                )
                return RowOutcome(None, reject)
        else:
            currency = self.default_currency

        title = str(values["title"]).strip()
        offer = {
            "external_sku": str(values["external_sku"]).strip(),
            "barcode": _stringify(values.get("barcode")),
            "brand": _stringify(values.get("brand")),
            "title": title,
            "title_normalized": title.lower(),
            "price": values["price"],
            "currency": currency,
            "stock": int(values["stock"]),
        }
        return RowOutcome(offer, soft)
