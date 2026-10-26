from datetime import datetime,timezone
from api.database import transactions_collection,realtime_analytics_collection

def create_transaction(user_id,symbol,side,quantity,price,timestamp=None,fees=0.0):
    symbol=symbol.upper(); side=side.upper()
    if side=="SELL":
        available=0.0
        for t in transactions_collection.find({"user_id":user_id,"symbol":symbol}):
            q=float(t["quantity"])
            available += q if t["side"].upper()=="BUY" else -q
        if quantity>available+1e-12: raise ValueError(f"Cannot sell {quantity} {symbol}; only {available} available.")
    if timestamp is None: timestamp=datetime.now(timezone.utc)
    transaction={"user_id":user_id,"symbol":symbol,"side":side,"quantity":float(quantity),"price":float(price),"timestamp":timestamp,"fees":float(fees)}
    result=transactions_collection.insert_one(transaction); transaction["_id"]=result.inserted_id
    return transaction

def get_portfolio(user_id):
    transactions=list(transactions_collection.find({"user_id":user_id}).sort("timestamp",1))
    holdings={}
    for t in transactions:
        s=t["symbol"]; side=t["side"].upper(); q=float(t["quantity"]); p=float(t["price"]); f=float(t.get("fees",0.0))
        h=holdings.setdefault(s,{"quantity":0.0,"cost_basis":0.0,"total_fees":0.0}); h["total_fees"]+=f
        if side=="BUY": h["quantity"]+=q; h["cost_basis"]+=q*p
        elif side=="SELL":
            avg=h["cost_basis"]/h["quantity"] if h["quantity"]>0 else 0.0
            h["cost_basis"]-=q*avg; h["quantity"]-=q
    result=[]; total_cost=0.0; total_value=0.0
    for symbol,h in holdings.items():
        q=h["quantity"]
        if q<=1e-12: continue
        avg=h["cost_basis"]/q if q>0 else 0.0
        latest=realtime_analytics_collection.find_one({"symbol":symbol},sort=[("timestamp",-1)])
        price=float(latest["market"]["close"]) if latest and latest.get("market") else 0.0
        value=q*price; pnl=value-h["cost_basis"]; pct=(pnl/h["cost_basis"]*100) if h["cost_basis"]>0 else 0.0
        result.append({"symbol":symbol,"quantity":q,"average_cost":avg,"cost_basis":h["cost_basis"],"current_price":price,"current_value":value,"unrealized_pnl":pnl,"pnl_percent":pct,"total_fees":h["total_fees"]})
        total_cost+=h["cost_basis"]; total_value+=value
    pnl=total_value-total_cost; pct=(pnl/total_cost*100) if total_cost>0 else 0.0
    return {"user_id":user_id,"holdings":result,"portfolio_summary":{"total_cost_basis":total_cost,"total_current_value":total_value,"total_unrealized_pnl":pnl,"total_pnl_percent":pct}}
