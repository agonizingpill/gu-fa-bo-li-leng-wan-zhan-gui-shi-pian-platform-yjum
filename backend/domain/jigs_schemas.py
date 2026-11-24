from typing import Annotated

from pydantic import BaseModel, ConfigDict, FiniteFloat, StringConstraints

class Calibrate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    jig: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    max_throw: FiniteFloat
