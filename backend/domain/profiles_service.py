from sqlalchemy import select

from core.queueing import submit, result
from core.records import get, insert, need, scan, update
from domain.jigs_model import jigs
from domain.coupons_model import coupons
from domain.profiles_model import profiles
from domain.work_orders_model import work_orders


def fit_curve(conn, user, data):
    coupon = get(conn, coupons, data.coupon)
    need(coupon['locked'], '试片尚未经过尺规见证')
    need(.001 <= data.penalty <= .3, '正则强度超出试制档范围')
    history = [item for item in scan(conn, coupons) if item['locked'] and item['code'] != data.coupon]
    need(len(history) >= 12, '已确认历史少于十二张')
    return submit(user, {'history':history,'coupon':coupon,'penalty':data.penalty})


def sign_profile(conn, user, data):
    run = result(user, data.token)
    target, metric = run['input']['coupon'], run['result']
    current = get(conn, coupons, target['code'])
    need(current == target, '试片与拟合快照不相容')
    need(metric['prediction'] > 0 and metric['mae'] < 5, '曲线超过台面验证误差预算')
    return insert(conn, profiles, code=data.code, coupon=target['code'], prediction=metric['prediction'],
        mae=metric['mae'], curve={'terms':metric['terms'],'held_out':metric['held_out']}, token=data.token)
