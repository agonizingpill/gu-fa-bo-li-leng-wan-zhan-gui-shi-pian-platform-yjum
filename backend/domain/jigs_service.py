from sqlalchemy import select

from core.queueing import submit, result
from core.records import get, insert, need, scan, update
from domain.jigs_model import jigs
from domain.coupons_model import coupons
from domain.profiles_model import profiles
from domain.work_orders_model import work_orders


def calibrate(conn, user, data):
    jig = get(conn, jigs, data.jig, lock=True)
    need(1 <= data.max_throw <= jig['spread']/3, '行程与台面跨度不相容')
    return update(conn, jigs, data.jig, max_throw=data.max_throw, calibrated=True)
