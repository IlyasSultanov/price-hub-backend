import uuid

from fastapi import APIRouter, Depends, Query

from app.core.depends import get_service_suppliers
from app.core.security import require_roles
from app.models import Supplier
from app.schemas import SupplierCreate, SupplierRead
from app.service.crud import CrudSuppliers
from app.utils import UserRole

router = APIRouter(
    prefix="/suppliers",
    tags=["Suppliers"],
    dependencies=[
        Depends(require_roles(UserRole.CATALOG_ADMIN, UserRole.SYSTEM_ADMIN))
    ],
)


@router.get("/all", response_model=list[SupplierRead])
async def get_all_suppliers(
    skip: int = Query(
        0,
        ge=0,
    ),
    limit: int = Query(10, ge=0, le=100),
    service: CrudSuppliers = Depends(get_service_suppliers),
) -> list[Supplier] | None:
    return await service.get_all(skip=skip, limit=limit)


@router.get("/{id}", response_model=SupplierRead)
async def get_supplier(
    id: uuid.UUID, service: CrudSuppliers = Depends(get_service_suppliers)
) -> Supplier | None:
    return await service.get_id(id)


@router.post("/create", response_model=SupplierRead)
async def create_supplier(
    data: SupplierCreate, service: CrudSuppliers = Depends(get_service_suppliers)
) -> Supplier | None:
    return await service.create(data)
