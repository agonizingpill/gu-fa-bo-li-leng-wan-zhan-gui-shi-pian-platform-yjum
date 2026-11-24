from fastapi import HTTPException
from sqlalchemy import select

from core import queueing
from core.records import get, insert, need, scan
from domain.coupons_model import plate_reports
from domain.coupons_service import fit_snapshot, save_plate_report
from domain.coupons_model import coupons
from domain.profiles_model import profiles


_FIT_FIELDS = ('jig', 'heat', 'thick', 'target', 'measured', 'locked')


def submit(user, payload):
    # 保留模块级 submit 名称，同时让 monkeypatch core.queueing.submit 也生效。
    return queueing.submit(user, payload)


def result(user, token):
    return queueing.result(user, token)


def view(user, token):
    return queueing.view(user, token)


def fit_curve(conn, user, data):
    coupon = get(conn, coupons, data.coupon)
    need(coupon['locked'], '试片尚未经过尺规见证')
    need(.001 <= data.penalty <= .3, '正则强度超出试制档范围')

    locked_history = [
        item for item in scan(conn, coupons)
        if item['locked'] and item['code'] != data.coupon
    ]
    need(len(locked_history) >= 12, '已确认历史少于十二张')

    snapshot = fit_snapshot(conn, data.coupon)
    # 十二张是“已确认历史”的入场校验；隔离/冲突母板会在快照分组中被排除。
    # 若排除后无法训练或留验，worker 会把对应计算任务标记为 rejected。
    payload = {'penalty': data.penalty, **snapshot}
    queued = submit(user, payload)
    save_plate_report(conn, queued['token'], data.coupon, snapshot)
    return queued


def sign_profile(conn, user, data):
    run = result(user, data.token)
    target, metric = run['input']['coupon'], run['result']
    current = get(conn, coupons, target['code'])

    # 母板合并会改变 plate/side/excluded 等追溯字段；拟合快照仍代表排队当时
    # 的完整分组。这里保留基线试片字段的相容性校验，忽略分组追溯字段。
    for key in _FIT_FIELDS:
        need(current.get(key) == target.get(key), '试片与拟合快照不相容')
    need(current['code'] == target['code'], '试片与拟合快照不相容')
    need(metric['prediction'] > 0 and metric['mae'] < 5, '曲线超过台面验证误差预算')

    plate_report = metric.get('plate_report') or run['input'].get('plate_report')
    curve = {'terms': metric['terms'], 'held_out': metric['held_out']}
    if plate_report:
        curve['plates'] = plate_report.get('plates', []) if isinstance(plate_report, dict) else plate_report
        curve['plate_report'] = plate_report

    return insert(conn, profiles, code=data.code, coupon=target['code'],
        prediction=metric['prediction'], mae=metric['mae'], curve=curve, token=data.token)


def _report_from_profile(conn, profile_row):
    curve = profile_row.get('curve') or {}
    report = curve.get('plate_report')
    if not report and curve.get('plates'):
        report = {'plates': curve['plates']}
    if not report and profile_row.get('token'):
        row = conn.execute(
            select(plate_reports).where(plate_reports.c.token == profile_row['token'])
        ).mappings().first()
        if row:
            stored = dict(row)
            report = stored.get('report')
    if not report:
        raise HTTPException(404, detail='该曲线没有母板分组快照')
    if isinstance(report, list):
        report = {'plates': report}
    return report


def get_plate_report(conn, user, token=None, code=None, profile=None, profile_code=None):
    profile_code = code or profile or profile_code
    if token:
        row = conn.execute(
            select(plate_reports).where(plate_reports.c.token == token)
        ).mappings().first()
        if row is None:
            # 兼容没有落 plate_reports 的旧任务：从计算结果读取。
            try:
                run = view(user, token)
                metric = run.get('result') or {}
                report = metric.get('plate_report') or run.get('input', {}).get('plate_report')
                if report:
                    row = {'token': token, 'coupon': run.get('input', {}).get('coupon', {}).get('code'),
                           'revision': run.get('input', {}).get('grouping_revision'),
                           'report': report}
            except HTTPException:
                row = None
        need(row is not None, '找不到该拟合编号的母板分组快照')
        stored = dict(row)
        report = stored.get('report') or {}
        if isinstance(report, list):
            report = {'plates': report}
        report.update({
            'token': token,
            'coupon': stored.get('coupon'),
            'revision': stored.get('revision'),
        })
        return report

    if profile_code:
        profile_row = get(conn, profiles, profile_code)
        report = _report_from_profile(conn, profile_row)
        report.update({
            'code': profile_code,
            'profile': profile_code,
            'token': profile_row.get('token'),
        })
        return report

    raise HTTPException(400, detail='请提供拟合编号 token 或曲线版本编号 code')


plate_report = get_plate_report
get_allocation = get_plate_report
