from sqlalchemy import select

from core.queueing import submit, result
from core.records import get, insert, need, scan, update
from domain.jigs_model import jigs
from domain.coupons_model import coupons
from domain.profiles_model import profiles
from domain.work_orders_model import work_orders


def record_coupon(conn, user, data):
    jig = get(conn, jigs, data.jig)
    need(jig['calibrated'], '弯模量具尚未确认')
    need(350 <= data.heat <= 650 and 1.5 <= data.thick <= 10, '超出试制保温或片厚范围')
    need(0 <= data.measured <= jig['max_throw'] and 0 < data.target <= jig['max_throw'], '试片超过弯模行程')
    return insert(conn, coupons, **data.model_dump(), locked=False)


def witness(conn, user, data):
    get(conn, coupons, data.coupon, lock=True)
    return update(conn, coupons, data.coupon, locked=True)
