from fastapi import APIRouter,Depends,HTTPException
from api.auth.auth_dependencies import get_current_user
from api.models.portfolio_models import TransactionCreate
from api.portfolio.portfolio_service import create_transaction,get_portfolio
from api.portfolio.personalized_service import get_personalized_analytics
from api.portfolio.recommendation_service import generate_recommendations
router=APIRouter(prefix="/portfolio",tags=["Portfolio"])
@router.get("")
def portfolio(current_user=Depends(get_current_user)): return get_portfolio(str(current_user["_id"]))
@router.post("/transactions")
def add_transaction(payload:TransactionCreate,current_user=Depends(get_current_user)):
    try:
        t=create_transaction(str(current_user["_id"]),payload.symbol,payload.side,payload.quantity,payload.price,payload.timestamp,payload.fees)
    except ValueError as exc: raise HTTPException(status_code=400,detail=str(exc))
    return {"success":True,"data":{"id":str(t["_id"]),"user_id":t["user_id"],"symbol":t["symbol"],"side":t["side"],"quantity":t["quantity"],"price":t["price"],"timestamp":t["timestamp"],"fees":t["fees"]}}
@router.get("/transactions")
def transactions(current_user=Depends(get_current_user)):
    from api.database import transactions_collection
    rows=list(transactions_collection.find({"user_id":str(current_user["_id"])}).sort("timestamp",-1))
    for r in rows: r["id"]=str(r.pop("_id"))
    return {"count":len(rows),"data":rows}


@router.get("/analytics")
def analytics(current_user=Depends(get_current_user)):
    result = get_personalized_analytics(str(current_user["_id"]), current_user.get("risk_tolerance", "medium"))
    result["username"] = current_user["username"]
    return result

@router.get("/recommendations")
def recommendations(current_user=Depends(get_current_user)):
    result = generate_recommendations(str(current_user["_id"]), current_user.get("risk_tolerance", "medium"))
    result["username"] = current_user["username"]
    return result
