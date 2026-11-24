import numpy as np
from sklearn.linear_model import Lasso
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from domain.plate_support import HOLDOUT, TRAIN, build_plate_report


def features(row):
    return [row[key] for key in ('heat', 'thick', 'target')]


def _grouped_rows(data):
    """返回按母板完整分组的 train/holdout。

    新任务的 input 中带有 fit 时固化的 plate_report，因此 worker 中断重跑也
    不会改用合并后的新分组。旧任务/旧测试没有快照时退回历史行为。
    """
    history = data.get('history', [])
    by_code = {row.get('code'): row for row in history if row.get('code') is not None}
    report = data.get('plate_report')
    if report is None and (data.get('groups') or data.get('allocation')):
        report = data.get('allocation') or {'plates': data.get('groups')}

    if report is None and any(row.get('plate') or row.get('plate_code') for row in history):
        report = build_plate_report(history, include_unlocked=True)

    groups = None
    if isinstance(report, dict):
        groups = report.get('plates') or report.get('groups')
    elif isinstance(report, list):
        groups = report

    if groups:
        train_codes = []
        holdout_codes = []
        for group in groups:
            if not isinstance(group, dict) or group.get('excluded'):
                continue
            side = group.get('side') or group.get('split')
            if side == TRAIN:
                train_codes.extend(group.get('train_coupons') or group.get('train') or [])
            elif side == HOLDOUT:
                holdout_codes.extend(group.get('holdout_coupons') or group.get('holdout') or [])
        train = [by_code[code] for code in train_codes if code in by_code]
        holdout = [by_code[code] for code in holdout_codes if code in by_code]
        if train or holdout:
            return train, holdout

    archive = sorted(history, key=lambda row: row['heat'])
    holdout = [row for index, row in enumerate(archive) if index % 4 == 0]
    train = [row for index, row in enumerate(archive) if index % 4 != 0]
    return train, holdout


def calculate(data):
    train, holdout = _grouped_rows(data)
    if not train:
        raise ValueError('训练分组为空，请检查母板登记和合并状态')
    if not holdout:
        raise ValueError('留验分组为空，需有未冲突的留验母板')

    train = sorted(train, key=lambda row: row['heat'])
    holdout = sorted(holdout, key=lambda row: row['heat'])
    model = make_pipeline(PolynomialFeatures(degree=2, include_bias=False),
                          StandardScaler(), Lasso(alpha=data['penalty'], max_iter=20000))
    model.fit([features(row) for row in train], [row['measured'] for row in train])
    errors = model.predict([features(row) for row in holdout]) - [row['measured'] for row in holdout]
    terms = model[0].get_feature_names_out(['温度', '片厚', '目标弯度'])

    report = data.get('plate_report')
    result = {
        'prediction': round(float(model.predict([features(data['coupon'])])[0]), 3),
        'mae': round(float(np.mean(np.abs(errors))), 3),
        'held_out': len(holdout),
        'terms': [term for term, coef in zip(terms, model[-1].coef_) if abs(coef) > 1e-10],
    }
    if report is not None:
        result['plate_report'] = report
        if isinstance(report, dict):
            result['plates'] = report.get('plates', [])
            result['allocation'] = report
            result['groups'] = report.get('plates', [])
            result['plate_allocations'] = report.get('assignments', [])
        elif isinstance(report, list):
            result['plates'] = report
            result['groups'] = report
    return result
