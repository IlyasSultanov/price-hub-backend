import enum


class StrEnum(str, enum.Enum):
    def __str__(self) -> str:
        return self.value


class SupplierStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    BLOCKED = "blocked"


class KeyTier(StrEnum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"


class FeedFormat(StrEnum):
    CSV = "csv"
    TSV = "tsv"
    XLSX = "xlsx"
    XML = "xml"
    PDF = "pdf"


class Currency(StrEnum):
    USD = "USD"
    EUR = "EUR"
    RUB = "RUB"
    GBP = "GBP"
    JPY = "JPY"
    CNY = "CNY"
    INR = "INR"
    BRL = "BRL"
    CAD = "CAD"
    AUD = "AUD"


class Severity(StrEnum):
    WARNING = "warning"
    ERROR = "error"


class TransformErrorCode(StrEnum):
    INVALID_BARCODE = "invalid_barcode"
    PRICE_NOT_NUMERIC = "price_not_numeric"
    STOCK_NOT_PARSEABLE = "stock_not_parseable"


class UserRole(StrEnum):
    SUPPLIER_MANAGER = "supplier_manager"
    CATALOG_ADMIN = "catalog_admin"
    SYSTEM_ADMIN = "system_admin"


class SourceType(StrEnum):
    UPLOAD = "upload"
    PRESIGNED = "presigned"
    HTTP = "http"
    FTP = "ftp"


class FeedStatus(StrEnum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PARSING = "parsing"
    VALIDATING = "validating"
    MATCHING = "matching"
    PRICING = "pricing"
    PUBLISHING = "publishing"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskIQEnum(StrEnum):
    pass
