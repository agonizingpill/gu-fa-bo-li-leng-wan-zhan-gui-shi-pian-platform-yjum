from sqlalchemy import Boolean, CheckConstraint, Column, Float, ForeignKey, Integer, JSON, String, Table

from core.db import metadata


coupons = Table('coupons', metadata,
    Column('code', String(64), primary_key=True),
    Column('jig', String(160), ForeignKey('jigs.code'), nullable=False),
    Column('heat', Float, nullable=False),
    Column('thick', Float, nullable=False),
    Column('target', Float, nullable=False),
    Column('measured', Float, nullable=False),
    Column('locked', Boolean, nullable=False),
    CheckConstraint('thick > 0'),
    CheckConstraint('measured >= 0'),
    CheckConstraint('target > 0'),
)
