from sqlalchemy import Boolean, CheckConstraint, Column, Float, ForeignKey, Integer, JSON, String, Table

from core.db import metadata


profiles = Table('profiles', metadata,
    Column('code', String(64), primary_key=True),
    Column('coupon', String(160), ForeignKey('coupons.code'), nullable=False),
    Column('prediction', Float, nullable=False),
    Column('mae', Float, nullable=False),
    Column('curve', JSON, nullable=False),
    Column('token', String(64), nullable=False, unique=True),
)
