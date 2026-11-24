from typing import Annotated

from pydantic import BaseModel, ConfigDict, FiniteFloat, StringConstraints

class RecordCoupon(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    jig: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    heat: FiniteFloat
    thick: FiniteFloat
    target: FiniteFloat
    measured: FiniteFloat


class Witness(BaseModel):
    model_config = ConfigDict(extra="forbid")
    coupon: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
