from typing import Annotated

from pydantic import BaseModel, ConfigDict, FiniteFloat, StringConstraints

class FitCurve(BaseModel):
    model_config = ConfigDict(extra="forbid")
    coupon: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    penalty: FiniteFloat


class SignProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    token: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
