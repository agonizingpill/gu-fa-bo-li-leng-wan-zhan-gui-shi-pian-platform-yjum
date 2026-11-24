from sqlalchemy import Boolean, CheckConstraint, Column, Float, ForeignKey, Integer, JSON, String, Table

from core.db import metadata


jigs = Table('jigs', metadata,
    Column('code', String(64), primary_key=True),
    Column('spread', Float, nullable=False),
    Column('max_throw', Float, nullable=False),
    Column('calibrated', Boolean, nullable=False),
    CheckConstraint('spread > 0'),
    CheckConstraint('max_throw > 0'),
)
