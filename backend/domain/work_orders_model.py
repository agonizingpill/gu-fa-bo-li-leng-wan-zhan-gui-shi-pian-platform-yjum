from sqlalchemy import Boolean, CheckConstraint, Column, Float, ForeignKey, Integer, JSON, String, Table

from core.db import metadata


work_orders = Table('work_orders', metadata,
    Column('code', String(64), primary_key=True),
    Column('profile', String(160), ForeignKey('profiles.code'), nullable=False),
    Column('jig', String(160), ForeignKey('jigs.code'), nullable=False),
    Column('slot', String(160), nullable=False, unique=True),
    Column('quantity', Integer, nullable=False),
    Column('state', String(160), nullable=False),
    CheckConstraint('quantity between 1 and 20'),
)
