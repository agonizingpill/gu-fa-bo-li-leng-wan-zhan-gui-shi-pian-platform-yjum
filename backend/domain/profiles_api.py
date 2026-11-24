from fastapi import APIRouter, Depends

from core.auth import actor, allow
from core.audit import record
from core.db import transaction
from core.records import scan
from domain import profiles_service as service
from domain.profiles_model import profiles
from domain.profiles_schemas import FitCurve, SignProfile

router = APIRouter()

@router.get('/profiles')
def list_profiles(user=Depends(actor)):
    with transaction() as conn:
        return scan(conn, profiles)


@router.post('/profiles/fit-curve')
def fit_curve(data: FitCurve, user=Depends(actor)):
    allow(user, ('operator', 'reviewer'))
    with transaction() as conn:
        output = service.fit_curve(conn, user, data)
        record(conn, user, 'profiles.fit_curve')
        return output


@router.post('/profiles/sign-profile')
def sign_profile(data: SignProfile, user=Depends(actor)):
    allow(user, ('reviewer',))
    with transaction() as conn:
        output = service.sign_profile(conn, user, data)
        record(conn, user, 'profiles.sign_profile')
        return output
