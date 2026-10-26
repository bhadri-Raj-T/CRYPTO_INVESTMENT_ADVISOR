from bson import ObjectId
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from api.auth.auth_service import decode_access_token
from api.database import users_collection

security=HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials=Depends(security)):
    try:
        payload=decode_access_token(credentials.credentials)
        user_id=payload.get("sub")
        if not user_id: raise HTTPException(status_code=401,detail="Invalid token")
        user=users_collection.find_one({"_id":ObjectId(user_id)})
        if not user: raise HTTPException(status_code=401,detail="User not found")
        return user
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid or expired token")
