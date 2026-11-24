from sqlalchemy import select

from core.queueing import submit, result
from core.records import get, insert, need, scan, update
from domain.jigs_model import jigs
from domain.coupons_model import coupons
from domain.profiles_model import profiles
from domain.work_orders_model import work_orders


def book_jig(conn, user, data):
    profile = get(conn, profiles, data.profile)
    coupon = get(conn, coupons, profile['coupon'])
    jig = get(conn, jigs, data.jig, lock=True)
    need(jig['calibrated'], '该机位弯模尚未检定')
    need(max(profile['prediction'], coupon['target']) <= jig['max_throw'], '夹具有效行程不足，机位未占用')
    need(1 <= data.quantity <= 20, '本炉试片数超额')
    return insert(conn, work_orders, **data.model_dump(), state='待打样')


def complete(conn, user, data):
    order = get(conn, work_orders, data.order, lock=True)
    need(order['state'] == '待打样', '委托已经签回')
    need(data.witness.startswith('W-'), '见证号需使用 W- 前缀')
    return update(conn, work_orders, data.order, state='已打样 '+data.witness)
