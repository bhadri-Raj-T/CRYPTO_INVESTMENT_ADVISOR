from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel
from api.auth.auth_dependencies import get_current_user
from api.database import users_collection
router=APIRouter(prefix="/profile",tags=["Profile"])
class RiskProfileUpdate(BaseModel):
    risk_tolerance:str
ALLOWED_RISK_TOLERANCE={"low","medium","high"}
@router.get("/risk")
def get_risk_profile(current_user=Depends(get_current_user)):
    return {"username":current_user["username"],"risk_tolerance":current_user.get("risk_tolerance","medium")}
@router.put("/risk")
def update_risk_profile(payload:RiskProfileUpdate,current_user=Depends(get_current_user)):
    risk_tolerance=payload.risk_tolerance.strip().lower()
    if risk_tolerance not in ALLOWED_RISK_TOLERANCE: raise HTTPException(status_code=400,detail="risk_tolerance must be one of: low, medium, high")
    users_collection.update_one({"_id":current_user["_id"]},{"$set":{"risk_tolerance":risk_tolerance}})
    return {"success":True,"username":current_user["username"],"risk_tolerance":risk_tolerance}
