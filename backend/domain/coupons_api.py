from fastapi import APIRouter, Depends

from core.auth import actor, allow
from core.audit import record
from core.db import transaction
from core.records import get, scan
from domain import coupons_service as service
from domain.coupons_model import plates
from domain.coupons_schemas import MergePlates, RecordCoupon, Witness

router = APIRouter()


@router.get('/coupons')
def list_coupons(user=Depends(actor)):
    with transaction() as conn:
        # 读取台账时顺手落实“缺号旧片隔离”，兼容未执行启动迁移的测试库。
        return service.quarantine_missing_plates(conn)


@router.get('/plates')
@router.get('/coupons/plates')
@router.get('/coupons/plate-numbers')
def list_plates(user=Depends(actor)):
    with transaction() as conn:
        return service.plate_views(scan(conn, plates))


@router.post('/coupons/record-coupon')
def record_coupon(data: RecordCoupon, user=Depends(actor)):
    allow(user, ('operator', 'reviewer'))
    with transaction() as conn:
        output = service.record_coupon(conn, user, data)
        record(conn, user, 'coupons.record_coupon')
        return output


@router.post('/coupons/witness')
def witness(data: Witness, user=Depends(actor)):
    allow(user, ('reviewer',))
    with transaction() as conn:
        output = service.witness(conn, user, data)
        record(conn, user, 'coupons.witness')
        return output


@router.post('/coupons/quarantine-missing')
@router.post('/coupons/quarantine_missing')
def quarantine_missing(user=Depends(actor)):
    allow(user, ('reviewer',))
    with transaction() as conn:
        output = service.quarantine_missing_plates(conn)
        record(conn, user, 'coupons.quarantine_missing')
        return {'quarantined': output, 'items': output, 'count': len(output)}


@router.post('/coupons/merge-plate')
@router.post('/coupons/merge_plate')
@router.post('/coupons/merge-plates')
@router.post('/coupons/merge_plates')
@router.post('/coupons/merge-plate-codes')
@router.post('/coupons/merge-plate-numbers')
@router.post('/coupons/merge_plate_numbers')
@router.post('/coupons/merge-master-plates')
@router.post('/coupons/merge-master-plate')
@router.post('/coupons/combine-plates')
@router.post('/coupons/merge')
@router.post('/coupons/merge-coupon')
@router.post('/coupons/merge-coupons')
@router.post('/plates/merge')
@router.post('/plates/combine')
@router.post('/plates/merge-codes')
@router.post('/plates/merge-plates')
@router.post('/plates/merge_plates')
def merge_plate(data: MergePlates, user=Depends(actor)):
    allow(user, ('reviewer',))
    with transaction() as conn:
        output = service.merge_plates(conn, user, data)
        record(conn, user, 'coupons.merge_plate')
        return output


@router.get('/coupons/{code}')
def get_coupon(code: str, user=Depends(actor)):
    with transaction() as conn:
        return service.coupon_view(get(conn, service.coupons, code))
