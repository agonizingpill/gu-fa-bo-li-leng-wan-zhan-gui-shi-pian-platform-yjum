import json
from sqlalchemy import func, select

from core.db import transaction
from domain.coupons_model import grouping_state, plates
from domain.demo import FIXTURES

def seed():
    sizes = {}
    with transaction() as conn:
        coupon_index = 0
        for table, rows in FIXTURES:
            for row in rows:
                present = conn.scalar(select(table.c.code).where(table.c.code == row['code']))
                if present is None:
                    values = dict(row)
                    if table.name == 'coupons' and not values.get('plate'):
                        # 演示账给每张历史试片独立母板号，使原每四条留一的
                        # 节奏落在母板分组上；真实旧库缺号记录仍由迁移隔离。
                        plate = f"MB-{coupon_index:02d}"
                        side = 'holdout' if coupon_index % 4 == 0 else 'train'
                        values.update(
                            plate=plate,
                            plate_original=plate,
                            side=side,
                            original_side=side,
                            quarantined=False,
                            excluded=False,
                            exclude_reason=None,
                        )
                        coupon_index += 1
                    conn.execute(table.insert().values(**values))
            sizes[table.name] = conn.scalar(select(func.count()).select_from(table))

        # 让母板号台账与演示试片保持一致。
        coupon_table = next(table for table, _ in FIXTURES if table.name == 'coupons')
        coupon_rows = conn.execute(select(coupon_table)).mappings().all()
        ordinal = 1
        for row in sorted(coupon_rows, key=lambda item: item['code']):
            plate_code = row.get('plate')
            if not plate_code:
                continue
            exists = conn.scalar(select(plates.c.code).where(plates.c.code == plate_code))
            if exists is None:
                side = row.get('original_side') or row.get('side') or 'train'
                if side not in ('train', 'holdout'):
                    side = 'train'
                conn.execute(plates.insert().values(
                    code=plate_code,
                    canonical_code=None,
                    ordinal=ordinal,
                    original_side=side,
                    side=side,
                    state='active',
                ))
            ordinal += 1

        state_exists = conn.scalar(select(grouping_state.c.id).where(grouping_state.c.id == 1))
        if state_exists is None:
            conn.execute(grouping_state.insert().values(id=1, revision=0))
    return sizes


if __name__ == '__main__':
    print(json.dumps(seed(), ensure_ascii=False, sort_keys=True))
