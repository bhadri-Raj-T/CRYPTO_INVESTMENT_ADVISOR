from fastapi import APIRouter, HTTPException

from api.services.model_service import (
    get_model_comparison,
    get_model_summary,
    get_symbol_model,
)

router = APIRouter(prefix="/models", tags=["Models"])


@router.get("/summary")
def model_summary():
    return get_model_summary()


@router.get("/comparison")
def model_comparison():
    return get_model_comparison()


@router.get("/{symbol}")
def symbol_model(symbol: str):
    result = get_symbol_model(symbol)
    if result is None:
        raise HTTPException(status_code=404, detail="Unsupported symbol")
    return result
