from datetime import datetime, timedelta, timezone
import bcrypt
from jose import jwt
from api.config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET
from api.database import users_collection

def hash_password(password):
    password_bytes=password.encode("utf-8")
    if len(password_bytes)>72: raise ValueError("Password cannot exceed 72 UTF-8 bytes")
    return bcrypt.hashpw(password_bytes,bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password, hashed_password):
    password_bytes=plain_password.encode("utf-8")
    if len(password_bytes)>72: return False
    return bcrypt.checkpw(password_bytes,hashed_password.encode("utf-8"))

def create_access_token(user_id,username):
    expire=datetime.now(timezone.utc)+timedelta(minutes=JWT_EXPIRE_MINUTES)
    return jwt.encode({"sub":user_id,"username":username,"exp":expire},JWT_SECRET,algorithm=JWT_ALGORITHM)

def decode_access_token(token):
    return jwt.decode(token,JWT_SECRET,algorithms=[JWT_ALGORITHM])

def create_user(username,password):
    if users_collection.find_one({"username":username}): return None
    now=datetime.now(timezone.utc)
    user={"username":username,"password_hash":hash_password(password),"risk_tolerance":"medium","created_at":now,"updated_at":now}
    result=users_collection.insert_one(user); user["_id"]=result.inserted_id
    return user

def authenticate_user(username,password):
    user=users_collection.find_one({"username":username})
    if not user or not verify_password(password,user["password_hash"]): return None
    return user
