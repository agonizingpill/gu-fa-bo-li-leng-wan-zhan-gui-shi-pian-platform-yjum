from fastapi import APIRouter, Depends, Request

from core.auth import actor, allow
from core.audit import record
from core.db import transaction
from core.records import get, scan
from domain import profiles_service as service
from domain.coupons_schemas import PlateReportQuery
from domain.profiles_model import profiles
from domain.profiles_schemas import FitCurve, SignProfile

router = APIRouter()


def _profile_view(row):
    item = dict(row)
    curve = item.get('curve') or {}
    report = None
    if isinstance(curve, dict):
        item['plates'] = curve.get('plates', [])
        report = curve.get('plate_report') or ({'plates': curve['plates']} if curve.get('plates') else None)
        item['plate_report'] = report
        terms = curve.get('terms') or []
        summary_parts = []
        if curve.get('held_out') is not None:
            summary_parts.append(f"留出 {curve['held_out']} 张")
        if terms:
            summary_parts.append(f"{len(terms)} 项显著特征")
        for key, value in curve.items():
            if key in ('plates', 'plate_report', 'terms', 'held_out'):
                continue
            summary_parts.append(f'{key} {value}')
        item['curve_summary'] = ' / '.join(summary_parts) or '—'
    else:
        item['curve_summary'] = '—'
    if isinstance(report, dict):
        counts = report.get('counts') or {}
        if not counts and report.get('plates'):
            plates = report['plates']
            counts = {
                'train_plates': sum(x.get('side') == 'train' for x in plates),
                'holdout_plates': sum(x.get('side') == 'holdout' for x in plates),
                'excluded_plates': sum(bool(x.get('excluded')) for x in plates),
            }
        item['plate_summary'] = '训练 {train_plates} · 留验 {holdout_plates} · 排除 {excluded_plates}'.format(**{
            'train_plates': counts.get('train_plates', 0),
            'holdout_plates': counts.get('holdout_plates', 0),
            'excluded_plates': counts.get('excluded_plates', 0),
        })
    else:
        item['plate_summary'] = '—'
    return item


@router.get('/profiles')
def list_profiles(user=Depends(actor)):
    with transaction() as conn:
        return [_profile_view(row) for row in scan(conn, profiles)]


@router.post('/profiles/fit-curve')
def fit_curve(data: FitCurve, user=Depends(actor)):
    allow(user, ('operator', 'reviewer'))
    with transaction() as conn:
        output = service.fit_curve(conn, user, data)
        record(conn, user, 'profiles.fit_curve')
        return output


@router.post('/profiles/sign-profile')
def sign_profile(data: SignProfile, user=Depends(actor)):
    allow(user, ('reviewer',))
    with transaction() as conn:
        output = service.sign_profile(conn, user, data)
        record(conn, user, 'profiles.sign_profile')
        return output


@router.get('/profiles/plate-report')
@router.get('/profiles/plate_report')
@router.get('/profiles/plate-allocation')
@router.get('/profiles/plate_allocation')
@router.get('/profiles/plate-trace')
@router.get('/profiles/plate_trace')
@router.get('/profiles/plate-lineage')
@router.get('/profiles/lineage')
@router.get('/profiles/grouping')
@router.get('/profiles/groups')
@router.get('/profiles/plate-split')
@router.get('/profiles/plates')
@router.get('/plates/report')
@router.get('/plates/allocation')
@router.get('/plates/trace')
def plate_report_get(request: Request, user=Depends(actor)):
    q = request.query_params
    token = q.get('token') or q.get('compute_token') or q.get('fit_token')
    code = q.get('code') or q.get('profile') or q.get('profile_code')
    with transaction() as conn:
        return service.get_plate_report(conn, user, token=token, code=code)


@router.get('/profiles/plate-assignments')
@router.get('/profiles/assignments')
@router.get('/profiles/allocations')
def plate_assignments_get(request: Request, user=Depends(actor)):
    q = request.query_params
    with transaction() as conn:
        report = service.get_plate_report(
            conn, user,
            token=q.get('token') or q.get('compute_token'),
            code=q.get('code') or q.get('profile'),
        )
        return report.get('plates', [])


@router.post('/profiles/plate-assignments')
@router.post('/profiles/assignments')
@router.post('/profiles/allocations')
def plate_assignments_post(data: PlateReportQuery, user=Depends(actor)):
    token = data.token or data.compute_token or data.fit_token
    code = data.code or data.profile or data.profile_code
    with transaction() as conn:
        report = service.get_plate_report(conn, user, token=token, code=code)
        return report.get('plates', [])


@router.get('/profiles/plate-report/{token}')
@router.get('/profiles/plate-trace/{token}')
@router.get('/profiles/plate-allocation/{token}')
@router.get('/compute/{token}/plates')
def plate_report_by_token_path(token: str, user=Depends(actor)):
    with transaction() as conn:
        return service.get_plate_report(conn, user, token=token)


@router.get('/profiles/by-code/{code}/plate-report')
@router.get('/profiles/{code}/plate-report')
def plate_report_by_profile_path(code: str, user=Depends(actor)):
    with transaction() as conn:
        return service.get_plate_report(conn, user, code=code)


@router.post('/profiles/plate-report')
@router.post('/profiles/plate_report')
@router.post('/profiles/plate-allocation')
@router.post('/profiles/plate_allocation')
@router.post('/profiles/plate-trace')
@router.post('/profiles/plate_trace')
@router.post('/profiles/plate-lineage')
@router.post('/profiles/lineage')
@router.post('/profiles/grouping')
@router.post('/profiles/plate-split')
@router.post('/profiles/plates')
@router.post('/plates/report')
@router.post('/plates/allocation')
def plate_report_post(request: Request, data: PlateReportQuery | None = None, user=Depends(actor)):
    allow(user, ('operator', 'reviewer', 'viewer'))
    data = data or PlateReportQuery()
    q = request.query_params
    token = data.token or data.compute_token or data.fit_token or q.get('token')
    code = data.code or data.profile or data.profile_code or q.get('code')
    with transaction() as conn:
        return service.get_plate_report(conn, user, token=token, code=code)


@router.get('/profiles/{code}')
def get_profile(code: str, user=Depends(actor)):
    with transaction() as conn:
        return _profile_view(get(conn, profiles, code))
