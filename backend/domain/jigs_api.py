from fastapi import APIRouter, Depends

from core.auth import actor, allow
from core.audit import record
from core.db import transaction
from core.records import scan
from domain import jigs_service as service
from domain.jigs_model import jigs
from domain.jigs_schemas import Calibrate

router = APIRouter()

@router.get('/jigs')
def list_jigs(user=Depends(actor)):
    with transaction() as conn:
        return scan(conn, jigs)


@router.post('/jigs/calibrate')
def calibrate(data: Calibrate, user=Depends(actor)):
    allow(user, ('reviewer',))
    with transaction() as conn:
        output = service.calibrate(conn, user, data)
        record(conn, user, 'jigs.calibrate')
        return output
