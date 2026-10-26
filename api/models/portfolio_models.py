from datetime import datetime
from pydantic import BaseModel, Field, field_validator

class TransactionCreate(BaseModel):
    symbol:str
    side:str
    quantity:float=Field(gt=0)
    price:float=Field(gt=0)
    timestamp:datetime|None=None
    fees:float=Field(default=0.0,ge=0)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls,value):
        value=value.upper().strip()
        allowed_symbols={"BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT"}
        if value not in allowed_symbols: raise ValueError(f"Unsupported symbol. Allowed symbols: {sorted(allowed_symbols)}")
        return value

    @field_validator("side")
    @classmethod
    def validate_side(cls,value):
        value=value.upper().strip()
        if value not in {"BUY","SELL"}: raise ValueError("side must be BUY or SELL")
        return value

class TransactionResponse(BaseModel):
    id:str
    user_id:str
    symbol:str
    side:str
    quantity:float
    price:float
    timestamp:datetime
    fees:float
