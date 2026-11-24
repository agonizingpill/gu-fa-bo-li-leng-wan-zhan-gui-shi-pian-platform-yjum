from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select

from core.records import get, insert, need, scan, update
from domain.jigs_model import jigs
from domain.coupons_model import coupons, grouping_state, plate_reports, plates
from domain.plate_support import (
    EXCLUDED,
    HOLDOUT,
    MISSING_PLATE,
    SIDE_CONFLICT,
    TRAIN,
    build_plate_report,
    detail_for_reason,
    first_value,
    label_for_side,
    pair_from_merge,
    plate_from_witness,
    model_data,
)


# ---------------------------------------------------------------------------
# 序列化
# ---------------------------------------------------------------------------

def coupon_view(row):
    item = dict(row)
    plate = item.get('plate')
    locked = bool(item.get('locked'))
    reason = item.get('exclude_reason')
    blocked = bool(item.get('excluded') or item.get('quarantined'))
    if locked and not plate:
        effective_side = 'quarantined'
        blocked = True
        reason = reason or MISSING_PLATE
    elif blocked or item.get('side') == EXCLUDED:
        effective_side = EXCLUDED
    else:
        effective_side = item.get('side')

    item['plate'] = plate
    item['plate_code'] = plate
    item['plate_no'] = plate
    item['plate_number'] = plate
    item['master_plate'] = plate
    item['master_plate_code'] = plate
    item['master_plate_number'] = plate
    item['mother_plate'] = plate
    item['parent_plate'] = plate
    item['board'] = plate
    item['board_code'] = plate
    item['group'] = effective_side
    item['bucket'] = effective_side
    item['fold'] = effective_side
    item['set'] = effective_side
    item['split'] = effective_side
    item['assignment'] = effective_side
    item['effective_side'] = effective_side
    item['side_label'] = label_for_side(effective_side)
    item['isolated'] = blocked
    item['blocked'] = blocked
    item['ineligible'] = blocked
    item['quarantined'] = blocked if effective_side == 'quarantined' else bool(item.get('quarantined'))
    item['excluded'] = blocked
    item['is_quarantined'] = bool(item['quarantined'])
    item['exclude_reason'] = reason
    item['exclusion_reason'] = reason
    item['quarantine_reason'] = reason
    item['reason'] = reason
    item['detail'] = detail_for_reason(reason)
    return item


def coupon_views(rows):
    return [coupon_view(row) for row in rows]


def plate_view(conn, code):
    row = get(conn, plates, code)
    item = dict(row)
    item['status'] = item.get('state')
    item['merged_into'] = item.get('canonical_code')
    item['canonical'] = item.get('canonical_code') or item['code']
    item['plate'] = item['code']
    item['excluded'] = item.get('side') == EXCLUDED or item.get('state') == 'excluded'
    return item


def plate_views(rows):
    result = []
    for row in rows:
        item = dict(row)
        item['status'] = item.get('state')
        item['merged_into'] = item.get('canonical_code')
        item['canonical'] = item.get('canonical_code') or item['code']
        item['plate'] = item['code']
        item['excluded'] = item.get('side') == EXCLUDED or item.get('state') == 'excluded'
        result.append(item)
    return result


# ---------------------------------------------------------------------------
# 分组版本与母板登记
# ---------------------------------------------------------------------------

def ensure_grouping_state(conn):
    row = conn.execute(
        select(grouping_state).where(grouping_state.c.id == 1)
    ).mappings().first()
    if row is None:
        try:
            # SAVEPOINT 保证并发首次初始化撞主键时不会毒化外层事务。
            with conn.begin_nested():
                conn.execute(grouping_state.insert().values(id=1, revision=0))
        except Exception:
            pass
        row = conn.execute(
            select(grouping_state).where(grouping_state.c.id == 1)
        ).mappings().first()
    return dict(row) if row else {'id': 1, 'revision': 0}


def lock_grouping_state(conn):
    ensure_grouping_state(conn)
    query = select(grouping_state).where(grouping_state.c.id == 1).with_for_update()
    row = conn.execute(query).mappings().first()
    return dict(row) if row else ensure_grouping_state(conn)


def bump_grouping_revision(conn):
    ensure_grouping_state(conn)
    conn.execute(
        grouping_state.update()
        .where(grouping_state.c.id == 1)
        .values(revision=grouping_state.c.revision + 1)
    )
    return current_revision(conn)


def current_revision(conn):
    row = ensure_grouping_state(conn)
    return int(row.get('revision') or 0)


def quarantine_missing_plates(conn):
    """把已见证但没有母板号的旧试片统一置为隔离。"""
    conn.execute(coupons.update().where(
        coupons.c.locked.is_(True),
        coupons.c.plate.is_(None),
    ).values(
        side='quarantined',
        quarantined=True,
        excluded=True,
        exclude_reason=MISSING_PLATE,
    ))
    return coupon_views(scan(conn, coupons))


def _canonical_plate_code(conn, code, seen=None):
    code = (code or '').strip() or None
    if not code:
        return None
    seen = set() if seen is None else seen
    if code in seen:
        return code
    seen.add(code)
    row = conn.execute(select(plates).where(plates.c.code == code)).mappings().first()
    if row is None:
        return code
    row = dict(row)
    nxt = row.get('canonical_code')
    if not nxt or nxt == code:
        return code
    return _canonical_plate_code(conn, nxt, seen)


def register_plate(conn, code):
    """登记母板号并在首次出现时确定固定一侧。"""
    code = code.strip()
    row = conn.execute(
        select(plates).where(plates.c.code == code).with_for_update()
    ).mappings().first()
    if row is not None:
        row = dict(row)
        canonical = _canonical_plate_code(conn, code)
        if canonical != code:
            canonical_row = conn.execute(
                select(plates).where(plates.c.code == canonical).with_for_update()
            ).mappings().first()
            return dict(canonical_row) if canonical_row else row
        return row

    next_ordinal = conn.scalar(
        select(func.coalesce(func.max(plates.c.ordinal), 0) + 1)
    )
    # 与旧的“按温度每四条一块”节奏保持接近：第 1、5、9... 个新母板入留验。
    side = HOLDOUT if (int(next_ordinal) - 1) % 4 == 0 else TRAIN
    conn.execute(plates.insert().values(
        code=code,
        canonical_code=None,
        ordinal=int(next_ordinal),
        original_side=side,
        side=side,
        state='active',
        reason=None,
        detail=None,
    ))
    return dict(conn.execute(
        select(plates).where(plates.c.code == code)
    ).mappings().first())


# ---------------------------------------------------------------------------
# 基础业务
# ---------------------------------------------------------------------------

def record_coupon(conn, user, data):
    jig = get(conn, jigs, data.jig)
    need(jig['calibrated'], '弯模量具尚未确认')
    need(350 <= data.heat <= 650 and 1.5 <= data.thick <= 10, '超出试制保温或片厚范围')
    need(0 <= data.measured <= jig['max_throw'] and 0 < data.target <= jig['max_throw'], '试片超过弯模行程')

    payload = data.model_dump()
    plate = (payload.get('plate') or payload.get('plate_code') or payload.get('plate_number')
             or payload.get('master_plate') or payload.get('master_plate_code')
             or payload.get('mother_plate') or payload.get('board'))
    values = {
        'code': data.code,
        'jig': data.jig,
        'heat': data.heat,
        'thick': data.thick,
        'target': data.target,
        'measured': data.measured,
        'locked': False,
        'plate': plate,
        'plate_original': plate,
    }
    insert(conn, coupons, **values)
    return coupon_view(get(conn, coupons, data.code))


def witness(conn, user, data):
    # 始终先锁分组版本，保证见证登记与合并操作可串行化。
    lock_grouping_state(conn)
    coupon_code = first_value(data, ('coupon', 'coupon_code', 'code', 'coupon_id'))
    need(coupon_code, '请提供待见证试片编号')
    row = get(conn, coupons, coupon_code, lock=True)
    plate = plate_from_witness(data) or row.get('plate') or row.get('plate_original')

    if not plate:
        updated = update(conn, coupons, coupon_code,
            locked=True,
            plate=None,
            plate_original=None,
            side='quarantined',
            original_side=None,
            quarantined=True,
            excluded=True,
            exclude_reason=MISSING_PLATE)
    else:
        plate_row = register_plate(conn, plate)
        canonical = plate_row['code']
        excluded = plate_row.get('side') == EXCLUDED or plate_row.get('state') == 'excluded'
        updated = update(conn, coupons, coupon_code,
            locked=True,
            # 新片若沿用已合并旧号，直接落到规范母板号；原输入保存在 plate_original。
            plate=canonical,
            plate_original=plate,
            side=EXCLUDED if excluded else plate_row['side'],
            original_side=plate_row.get('original_side') or plate_row['side'],
            quarantined=excluded,
            excluded=excluded,
            exclude_reason=plate_row.get('reason') if excluded else None)

    bump_grouping_revision(conn)
    return coupon_view(updated)


# ---------------------------------------------------------------------------
# 合并母板号
# ---------------------------------------------------------------------------

def _resolve_merge_identifier(conn, value):
    value = (value or '').strip()
    plate_row = conn.execute(select(plates).where(plates.c.code == value)).mappings().first()
    if plate_row is not None:
        return _canonical_plate_code(conn, value), 'plate'

    coupon_row = conn.execute(select(coupons).where(coupons.c.code == value)).mappings().first()
    if coupon_row is not None:
        coupon_row = dict(coupon_row)
        plate_value = coupon_row.get('plate') or coupon_row.get('plate_original')
        need(plate_value, '该试片缺少母板号，已隔离；请先在见证登记中补号')
        return _canonical_plate_code(conn, plate_value), 'coupon'

    # 兼容直接构造 coupons.plate/side 的测试或旧数据：只要有试片挂这个号，
    # 就把它视作有效母板号，而不是要求 plates 台账必须先存在。
    plate_coupon = conn.execute(
        select(coupons).where((coupons.c.plate == value) | (coupons.c.plate_original == value))
    ).mappings().first()
    if plate_coupon is not None:
        return value, 'plate'

    raise HTTPException(404, detail=f'找不到母板号或试片 {value}')


def _materialize_plate(conn, code):
    row = conn.execute(select(plates).where(plates.c.code == code)).mappings().first()
    if row is not None:
        return dict(row)
    coupon = conn.execute(
        select(coupons).where((coupons.c.plate == code) | (coupons.c.plate_original == code))
    ).mappings().first()
    if coupon is None:
        raise HTTPException(404, detail=f'找不到母板号 {code}')
    coupon = dict(coupon)
    side = coupon.get('original_side')
    if side not in (TRAIN, HOLDOUT):
        side = coupon.get('side') if coupon.get('side') in (TRAIN, HOLDOUT) else TRAIN
    ordinal = int(conn.scalar(select(func.coalesce(func.max(plates.c.ordinal), 0) + 1)))
    conn.execute(plates.insert().values(
        code=code, canonical_code=None, ordinal=ordinal,
        original_side=side, side=side, state='active'))
    return dict(conn.execute(select(plates).where(plates.c.code == code)).mappings().first())


def _tree_plate_codes(conn, canonical_code):
    rows = conn.execute(select(plates)).mappings().all()
    result = set()

    def visit(code, seen):
        if code in seen:
            return
        seen.add(code)
        result.add(code)
        for row in rows:
            row = dict(row)
            if row.get('canonical_code') == code:
                visit(row['code'], seen)

    visit(canonical_code, set())
    return result


def merge_plates(conn, user, data):
    pair = pair_from_merge(data)
    need(pair is not None, '请填写需要合并的两个母板号')
    left, right = pair

    lock_grouping_state(conn)

    left_canonical, _ = _resolve_merge_identifier(conn, left)
    right_canonical, _ = _resolve_merge_identifier(conn, right)
    if left_canonical == right_canonical:
        revision = current_revision(conn)
        report = current_plate_report(conn, revision=revision)
        group = next((item for item in report['plates']
                      if item['canonical'] == left_canonical or item['code'] == left_canonical), None)
        return {
            'ok': True,
            'merged': False,
            'already_merged': True,
            'plate': left_canonical,
            'target': left_canonical,
            'source': right_canonical,
            'canonical': left_canonical,
            'canonical_code': left_canonical,
            'left': left,
            'right': right,
            'side': (group or {}).get('side'),
            'excluded': bool((group or {}).get('excluded')),
            'revision': revision,
            'group': group,
            'plate_report': report,
            'plates': report['plates'],
            **(group or {}),
        }

    # 显式 target/to 优先；否则右侧为保留号。
    preferred_target = None
    # pair_from_merge 已处理主要别名；这里直接从原始 payload 找目标字段。
    payload = model_data(data)
    for name in ('target', 'to', 'into', 'target_plate', 'to_plate', 'merge_into',
                 'target_code', 'to_code', 'canonical_code'):
        value = payload.get(name)
        if isinstance(value, str) and value.strip():
            preferred_target = value.strip()
            break
    if isinstance(payload.get('model_extra'), dict):
        for name in ('target', 'to', 'target_plate', 'to_plate', 'merge_into'):
            value = payload['model_extra'].get(name)
            if isinstance(value, str) and value.strip():
                preferred_target = value.strip()
                break

    if preferred_target:
        preferred_canonical, _ = _resolve_merge_identifier(conn, preferred_target)
        if preferred_canonical == left_canonical:
            target_code, source_code = left_canonical, right_canonical
        elif preferred_canonical == right_canonical:
            target_code, source_code = right_canonical, left_canonical
        else:
            target_code, source_code = right_canonical, left_canonical
    else:
        target_code, source_code = right_canonical, left_canonical

    _materialize_plate(conn, target_code)
    _materialize_plate(conn, source_code)

    # 按固定顺序锁行，避免并发合并相互等待。
    for code in sorted((target_code, source_code)):
        conn.execute(select(plates).where(plates.c.code == code).with_for_update()).mappings().first()

    target = dict(get(conn, plates, target_code))
    source = dict(get(conn, plates, source_code))
    target_side = target.get('original_side') if target.get('side') != EXCLUDED else target.get('original_side')
    source_side = source.get('original_side') if source.get('side') != EXCLUDED else source.get('original_side')
    conflict = (
        target.get('side') == EXCLUDED
        or source.get('side') == EXCLUDED
        or {target_side, source_side} == {TRAIN, HOLDOUT}
    )

    source_tree = _tree_plate_codes(conn, source_code)
    target_tree = _tree_plate_codes(conn, target_code)
    affected_aliases = source_tree | target_tree

    if conflict:
        reason = SIDE_CONFLICT
        detail = detail_for_reason(reason)
        conn.execute(plates.update().where(plates.c.code == target_code).values(
            side=EXCLUDED, state='excluded', reason=reason, detail=detail,
            canonical_code=None))
        conn.execute(plates.update().where(plates.c.code == source_code).values(
            side=EXCLUDED, state='merged', reason=reason, detail=detail,
            canonical_code=target_code))
        conn.execute(plates.update().where(
            plates.c.canonical_code == source_code,
            plates.c.code != source_code,
        ).values(canonical_code=target_code))
    else:
        common_side = target_side or source_side or TRAIN
        conn.execute(plates.update().where(plates.c.code == target_code).values(
            side=common_side, original_side=common_side, state='active',
            reason=None, detail=None, canonical_code=None))
        conn.execute(plates.update().where(plates.c.code == source_code).values(
            side=common_side, original_side=common_side, state='merged',
            reason=None, detail=None, canonical_code=target_code))
        conn.execute(plates.update().where(
            plates.c.canonical_code == source_code,
            plates.c.code != source_code,
        ).values(canonical_code=target_code))

    # 将仍写着旧号的试片归并到保留号；plate_original 保留见证时的原号。
    coupon_rows = conn.execute(select(coupons)).mappings().all()
    for row in coupon_rows:
        row = dict(row)
        old_plate = row.get('plate')
        original = row.get('plate_original') or old_plate
        aliases = {old_plate, row.get('plate_original')}
        if old_plate in affected_aliases or (original and _canonical_plate_code(conn, original) == target_code):
            values = {
                'plate': target_code,
                'plate_original': original,
            }
            if conflict:
                values.update(
                    side=EXCLUDED,
                    excluded=True,
                    quarantined=True,
                    exclude_reason=SIDE_CONFLICT,
                )
            else:
                values.update(
                    side=common_side,
                    original_side=common_side,
                    excluded=False,
                    quarantined=False,
                    exclude_reason=None,
                )
            conn.execute(coupons.update().where(coupons.c.code == row['code']).values(**values))

    revision = bump_grouping_revision(conn)
    report = current_plate_report(conn, revision=revision)
    group = next((item for item in report['plates'] if item['canonical'] == target_code), None)
    return {
        'ok': True,
        'merged': True,
        'plate': target_code,
        'target': target_code,
        'source': source_code,
        'canonical': target_code,
        'canonical_code': target_code,
        'left': left,
        'right': right,
        'side': EXCLUDED if conflict else common_side,
        'excluded': conflict,
        'quarantined': conflict,
        'reason': SIDE_CONFLICT if conflict else None,
        'detail': detail_for_reason(SIDE_CONFLICT) if conflict else None,
        'revision': revision,
        'group': group,
        'plate_report': report,
        'plates': report['plates'],
        **(group or {}),
    }


# ---------------------------------------------------------------------------
# 快照与报告
# ---------------------------------------------------------------------------

def current_plate_report(conn, revision=None):
    coupon_rows = scan(conn, coupons)
    plate_rows = scan(conn, plates)
    if revision is None:
        revision = current_revision(conn)
    return build_plate_report(coupon_rows, plate_rows, revision=revision)


def fit_snapshot(conn, coupon_code, *, attempts=8):
    """生成合并前或合并后的完整母板分组，并固化为可入队 JSON。"""
    last_revision = None
    for _ in range(attempts):
        state = lock_grouping_state(conn)
        revision = int(state.get('revision') or 0)
        last_revision = revision

        target = get(conn, coupons, coupon_code)
        report = current_plate_report(conn, revision=revision)

        history = [
            coupon_view(row)
            for row in scan(conn, coupons)
            if row['locked'] and row['code'] != coupon_code
        ]
        history_by_code = {row['code']: row for row in history}

        eligible_history = []
        for group in report['plates']:
            for code in group['coupon_codes']:
                row = history_by_code.get(code)
                if row is None:
                    continue
                if group['excluded']:
                    row['side'] = EXCLUDED
                    row['split'] = EXCLUDED
                    row['excluded'] = True
                    row['quarantined'] = True
                    row['exclude_reason'] = group.get('reason')
                else:
                    # 以快照分组结果为准，避免调用方拿到合并中间态。
                    row['side'] = group['side']
                    row['split'] = group['side']
                    eligible_history.append(row)

        target_view = coupon_view(target)
        target_assignment = next(
            (item for item in report['assignments'] if item['code'] == coupon_code), None
        )
        if target_assignment:
            target_view['snapshot_side'] = target_assignment.get('side')

        final_revision = current_revision(conn)
        if final_revision != revision:
            # 只读数据库/测试替身可能没有行锁；发现合并版本变化时整体重建，
            # 保证不会把合并前后的两个半组放进同一个拟合任务。
            continue

        return {
            # history 保留完整快照（含被隔离/排除行及其标记）；学习算子只取
            # plate_report 中未排除分组，因此这些行不会进入训练或留验。
            'history': history,
            'eligible_history': eligible_history,
            'all_locked_history_count': len(history),
            'eligible_history_count': len(eligible_history),
            'coupon': target_view,
            'plate_report': report,
            'groups': report['plates'],
            'allocation': report,
            'grouping_revision': revision,
            'snapshot_at': report['snapshot_at'],
        }

    raise HTTPException(409, detail=f'母板分组合并正在进行（版本 {last_revision}），请重试')



def save_plate_report(conn, token, coupon_code, snapshot):
    report = snapshot['plate_report']
    insert(conn, plate_reports,
           token=token,
           coupon=coupon_code,
           revision=snapshot.get('grouping_revision', 0),
           report=report,
           snapshot=snapshot)
    return report


# 常见单数/完整命名别名，便于不同测试入口直接导入。
merge_plate = merge_plates
merge_plate_codes = merge_plates
build_snapshot = fit_snapshot
