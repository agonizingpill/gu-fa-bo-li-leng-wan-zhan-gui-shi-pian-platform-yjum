"""母板号合并/分组的兼容模块。

主实现位于 coupons_service；这里保留独立 service 路径，方便按领域名导入。
"""
from domain.coupons_service import (  # noqa: F401
    build_snapshot,
    current_plate_report,
    fit_snapshot,
    merge_plate,
    merge_plate_codes,
    merge_plates,
    quarantine_missing_plates,
    register_plate,
)
from domain.plate_support import build_plate_report  # noqa: F401

__all__ = [
    'build_plate_report',
    'build_snapshot',
    'current_plate_report',
    'fit_snapshot',
    'merge_plate',
    'merge_plate_codes',
    'merge_plates',
    'quarantine_missing_plates',
    'register_plate',
]
