import re

from sqlalchemy.orm import DeclarativeBase, declared_attr

_CAMEL_BOUNDARY_RE = re.compile(r"(?<!^)(?=[A-Z])")


class Base(DeclarativeBase):
    __abstract__ = True

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return f"{_CAMEL_BOUNDARY_RE.sub('_', cls.__name__).lower()}s"
