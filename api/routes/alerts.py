from fastapi import APIRouter,Depends,Query
from api.auth.auth_dependencies import get_current_user
from api.portfolio.alert_service import generate_personalized_alerts,get_user_alerts,mark_alert_read
router=APIRouter(prefix="/alerts",tags=["Alerts"])
@router.post("/generate")
def generate_alerts(current_user=Depends(get_current_user)):
    alerts=generate_personalized_alerts(str(current_user["_id"]),current_user.get("risk_tolerance","medium"))
    return {"count":len(alerts),"data":alerts}
@router.get("")
def list_alerts(unread_only:bool=Query(default=False),limit:int=Query(default=100,ge=1,le=1000),current_user=Depends(get_current_user)):
    alerts=get_user_alerts(str(current_user["_id"]),unread_only,limit)
    return {"count":len(alerts),"data":alerts}
@router.post("/{alert_id}/read")
def read_alert(alert_id:str,current_user=Depends(get_current_user)):
    success=mark_alert_read(str(current_user["_id"]),alert_id)
    return {"success":success,"id":alert_id,"read":success}
