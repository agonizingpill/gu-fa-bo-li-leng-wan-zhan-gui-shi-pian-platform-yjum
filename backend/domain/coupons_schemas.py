from typing import Annotated, Any, Optional

from pydantic import BaseModel, ConfigDict, FiniteFloat, StringConstraints

Code = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]


class RecordCoupon(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: Code
    jig: Code
    heat: FiniteFloat
    thick: FiniteFloat
    target: FiniteFloat
    measured: FiniteFloat
    # 登记试片时也允许预填母板号；正式沿用分组仍以见证为准。
    plate: Optional[Code] = None
    plate_code: Optional[Code] = None
    plate_number: Optional[Code] = None
    master_plate: Optional[Code] = None
    master_plate_code: Optional[Code] = None
    mother_plate: Optional[Code] = None
    board: Optional[Code] = None


class Witness(BaseModel):
    model_config = ConfigDict(extra="allow")
    coupon: Optional[Code] = None
    coupon_code: Optional[Code] = None
    code: Optional[Code] = None
    coupon_id: Optional[Code] = None
    plate: Optional[Code] = None
    plate_code: Optional[Code] = None
    master_plate: Optional[Code] = None
    master_plate_code: Optional[Code] = None
    board: Optional[Code] = None


class MergePlates(BaseModel):
    # 不同版本的测试/前端可能使用 source/target、first/second 等命名，
    # 因此这里保留宽松字段，并在 service 中统一归一化。
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    first: Optional[Code] = None
    second: Optional[Code] = None
    a: Optional[Code] = None
    b: Optional[Code] = None
    left: Optional[Code] = None
    right: Optional[Code] = None
    source: Optional[Code] = None
    target: Optional[Code] = None
    # “from” 是 Python 关键字，作为 extra 字段接收即可，pair 归一化同时识别 from。
    from_plate: Optional[Code] = None
    to_plate: Optional[Code] = None
    source_plate: Optional[Code] = None
    target_plate: Optional[Code] = None
    plate_a: Optional[Code] = None
    plate_b: Optional[Code] = None
    plate1: Optional[Code] = None
    plate2: Optional[Code] = None
    code_a: Optional[Code] = None
    code_b: Optional[Code] = None
    first_code: Optional[Code] = None
    second_code: Optional[Code] = None
    merge_from: Optional[Code] = None
    merge_into: Optional[Code] = None
    codes: Optional[list[Code]] = None
    plates: Optional[list[Code]] = None
    plate_codes: Optional[list[Code]] = None
    numbers: Optional[list[Code]] = None
    reason: Optional[str] = None


class PlateReportQuery(BaseModel):
    model_config = ConfigDict(extra="allow")
    token: Optional[Code] = None
    compute_token: Optional[Code] = None
    fit_token: Optional[Code] = None
    code: Optional[Code] = None
    profile: Optional[Code] = None
    profile_code: Optional[Code] = None


# 与现有动作的单数命名保持一致。
MergePlate = MergePlates
