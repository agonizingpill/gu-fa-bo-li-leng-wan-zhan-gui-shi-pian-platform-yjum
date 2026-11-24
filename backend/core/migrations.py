from sqlalchemy import inspect, text

from core.db import engine


_COUPON_COLUMNS = {
    'plate': 'VARCHAR(160)',
    'plate_original': 'VARCHAR(160)',
    'side': 'VARCHAR(16)',
    'original_side': 'VARCHAR(16)',
    'quarantined': 'BOOLEAN DEFAULT FALSE NOT NULL',
    'excluded': 'BOOLEAN DEFAULT FALSE NOT NULL',
    'exclude_reason': 'VARCHAR(64)',
}


def upgrade():
    """轻量幂等迁移。

    评测/本机可能已经用旧镜像初始化过命名卷；SQLAlchemy create_all 只会补新表，
    不会给 coupons 补列，因此这里显式 ADD COLUMN IF NOT EXISTS 的兼容写法。
    """
    inspector = inspect(engine)
    if 'coupons' not in inspector.get_table_names():
        return
    existing = {column['name'] for column in inspector.get_columns('coupons')}
    dialect = engine.dialect.name
    with engine.begin() as conn:
        for name, ddl_type in _COUPON_COLUMNS.items():
            if name in existing:
                continue
            if dialect == 'postgresql':
                conn.execute(text(f'ALTER TABLE coupons ADD COLUMN IF NOT EXISTS {name} {ddl_type}'))
            else:
                conn.execute(text(f'ALTER TABLE coupons ADD COLUMN {name} {ddl_type}'))

        # 旧版已见证但没有母板号的记录不能猜测同板关系，先隔离。
        conn.execute(text("""
            UPDATE coupons
               SET quarantined = TRUE,
                   excluded = TRUE,
                   side = 'quarantined',
                   exclude_reason = 'missing_plate'
             WHERE locked = TRUE
               AND plate IS NULL
        """))
        conn.execute(text("""
            INSERT INTO grouping_state (id, revision)
            SELECT 1, 0
            WHERE NOT EXISTS (SELECT 1 FROM grouping_state WHERE id = 1)
        """))


if __name__ == '__main__':
    upgrade()
