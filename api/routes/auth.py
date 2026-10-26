from fastapi import APIRouter,HTTPException,Depends
from pydantic import BaseModel
from api.auth.auth_service import authenticate_user,create_access_token,create_user
from api.auth.auth_dependencies import get_current_user
router=APIRouter(prefix="/auth",tags=["Auth"])
class AuthPayload(BaseModel):
    username:str
    password:str
@router.post("/register")
def register(payload:AuthPayload):
    try: user=create_user(payload.username.strip(),payload.password)
    except ValueError as exc: raise HTTPException(status_code=400,detail=str(exc))
    if user is None: raise HTTPException(status_code=409,detail="Username already exists")
    return {"id":str(user["_id"]),"username":user["username"],"risk_tolerance":user.get("risk_tolerance","medium")}
@router.post("/login")
def login(payload:AuthPayload):
    user=authenticate_user(payload.username.strip(),payload.password)
    if not user: raise HTTPException(status_code=401,detail="Invalid username or password")
    return {"access_token":create_access_token(str(user["_id"]),user["username"]),"token_type":"bearer","user":{"id":str(user["_id"]),"username":user["username"],"risk_tolerance":user.get("risk_tolerance","medium")}}
@router.get("/me")
def me(current_user=Depends(get_current_user)):
    return {"id":str(current_user["_id"]),"username":current_user["username"],"risk_tolerance":current_user.get("risk_tolerance","medium")}
