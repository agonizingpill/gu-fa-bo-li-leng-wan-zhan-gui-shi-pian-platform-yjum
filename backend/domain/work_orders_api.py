from fastapi import APIRouter, Depends

from core.auth import actor, allow
from core.audit import record
from core.db import transaction
from core.records import scan
from domain import work_orders_service as service
from domain.work_orders_model import work_orders
from domain.work_orders_schemas import BookJig, Complete

router = APIRouter()

@router.get('/work_orders')
def list_work_orders(user=Depends(actor)):
    with transaction() as conn:
        return scan(conn, work_orders)


@router.post('/work_orders/book-jig')
def book_jig(data: BookJig, user=Depends(actor)):
    allow(user, ('operator', 'reviewer'))
    with transaction() as conn:
        output = service.book_jig(conn, user, data)
        record(conn, user, 'work_orders.book_jig')
        return output


@router.post('/work_orders/complete')
def complete(data: Complete, user=Depends(actor)):
    allow(user, ('reviewer',))
    with transaction() as conn:
        output = service.complete(conn, user, data)
        record(conn, user, 'work_orders.complete')
        return output
