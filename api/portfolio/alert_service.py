from datetime import datetime,timezone
from bson import ObjectId
from api.database import alerts_collection
from api.portfolio.personalized_service import get_personalized_analytics

def create_alert(user_id,symbol,alert_type,severity,message):
    alert={"user_id":user_id,"symbol":symbol,"type":alert_type,"severity":severity,"message":message,"created_at":datetime.now(timezone.utc),"read":False}
    result=alerts_collection.insert_one(alert); alert["_id"]=result.inserted_id; return alert

def generate_personalized_alerts(user_id,risk_tolerance):
    analytics=get_personalized_analytics(user_id,risk_tolerance); created=[]
    for asset in analytics["assets"]:
        s=asset["symbol"]; p=asset.get("prediction") or {}; r=asset.get("risk") or {}; a=asset.get("anomaly") or {}
        if a.get("is_anomaly") is True:
            created.append(create_alert(user_id,s,"ANOMALY","WARNING",f"{s}: unusual market behavior detected. Anomaly score: {float(a.get('score',0)):.2f}."))
        if r.get("level")=="HIGH":
            created.append(create_alert(user_id,s,"HIGH_RISK","HIGH",f"{s}: high market risk detected. Risk score: {float(r.get('score',0)):.2f}."))
        if p.get("direction")=="UP" and p.get("probability_up") is not None and float(p["probability_up"])>=0.60 and a.get("is_anomaly") is not True:
            created.append(create_alert(user_id,s,"POSITIVE_BIAS","INFO",f"{s}: model shows a positive directional bias with {float(p['probability_up'])*100:.2f}% probability of an upward move."))
        if p.get("direction")=="DOWN" and p.get("probability_down") is not None and float(p["probability_down"])>=0.60 and a.get("is_anomaly") is not True:
            created.append(create_alert(user_id,s,"NEGATIVE_BIAS","WARNING",f"{s}: model shows a negative directional bias with {float(p['probability_down'])*100:.2f}% probability of a downward move."))
    for a in created: a["id"]=str(a.pop("_id"))
    return created

def get_user_alerts(user_id,unread_only=False,limit=100):
    q={"user_id":user_id}
    if unread_only: q["read"]=False
    alerts=list(alerts_collection.find(q).sort("created_at",-1).limit(limit))
    for a in alerts: a["id"]=str(a.pop("_id"))
    return alerts

def mark_alert_read(user_id,alert_id):
    if not ObjectId.is_valid(alert_id): return False
    result=alerts_collection.update_one({"_id":ObjectId(alert_id),"user_id":user_id},{"$set":{"read":True}})
    return result.modified_count==1 or result.matched_count==1
