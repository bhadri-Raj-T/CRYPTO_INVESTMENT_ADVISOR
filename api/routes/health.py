from fastapi import APIRouter
from api.database import check_database
router=APIRouter(prefix="/health",tags=["Health"])
@router.get("")
def health_check():
    try:
        check_database()
        return {"status":"ok","database":"connected"}
    except Exception as exc:
        return {"status":"error","database":"disconnected","detail":str(exc)}
