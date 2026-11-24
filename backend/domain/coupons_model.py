from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Table,
    text,
)

from core.db import metadata


coupons = Table('coupons', metadata,
    Column('code', String(64), primary_key=True),
    Column('jig', String(160), ForeignKey('jigs.code'), nullable=False),
    Column('heat', Float, nullable=False),
    Column('thick', Float, nullable=False),
    Column('target', Float, nullable=False),
    Column('measured', Float, nullable=False),
    Column('locked', Boolean, nullable=False),
    # 母板追溯与拟合分组。旧记录的 plate 为空，按缺号隔离处理。
    Column('plate', String(160), nullable=True, index=True),
    Column('plate_original', String(160), nullable=True),
    Column('side', String(16), nullable=True),
    Column('original_side', String(16), nullable=True),
    Column('quarantined', Boolean, nullable=False, server_default=text('false')),
    Column('excluded', Boolean, nullable=False, server_default=text('false')),
    Column('exclude_reason', String(64), nullable=True),
    CheckConstraint('thick > 0'),
    CheckConstraint('measured >= 0'),
    CheckConstraint('target > 0'),
    CheckConstraint("side is null or side in ('train', 'holdout', 'excluded', 'quarantined')"),
)


plates = Table('plates', metadata,
    Column('code', String(160), primary_key=True),
    Column('canonical_code', String(160), nullable=True, index=True),
    Column('ordinal', Integer, nullable=False),
    Column('original_side', String(16), nullable=False),
    Column('side', String(16), nullable=False),
    Column('state', String(32), nullable=False, server_default='active'),
    Column('reason', String(64), nullable=True),
    Column('detail', String(255), nullable=True),
    CheckConstraint("original_side in ('train', 'holdout')"),
    CheckConstraint("side in ('train', 'holdout', 'excluded')"),
    CheckConstraint("state in ('active', 'merged', 'excluded')"),
)


grouping_state = Table('grouping_state', metadata,
    Column('id', Integer, primary_key=True),
    Column('revision', Integer, nullable=False, server_default='0'),
)


plate_reports = Table('plate_reports', metadata,
    Column('token', String(64), primary_key=True),
    Column('coupon', String(160), nullable=False),
    Column('revision', Integer, nullable=False, server_default='0'),
    Column('report', JSON, nullable=False),
    Column('snapshot', JSON, nullable=True),
    Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('CURRENT_TIMESTAMP')),
)
