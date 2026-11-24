from typing import Annotated

from pydantic import BaseModel, ConfigDict, FiniteFloat, StringConstraints

class BookJig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    profile: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    jig: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    slot: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    quantity: int


class Complete(BaseModel):
    model_config = ConfigDict(extra="forbid")
    order: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    witness: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
