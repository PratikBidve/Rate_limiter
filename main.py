from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
import time
from datetime import datetime

app = FastAPI()

@app.get('/')
async def main():
    return {"Creator" : "Mr. Prateek A Bidve"}

class LimitConfigRequest(BaseModel):
    endpoint: str = Field(..., pattern=r"^/[a-z0-9/_-]+$")
    max_requests: int = Field(..., gt=0)
    window_seconds: Literal[60,300,3600]
    
limits_db: dict[str, LimitConfigRequest] = {}
requests_db: dict[str, dict[str, dict]] = {}

class CheckRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    endpoint: str = Field(..., pattern=r"^/[a-z0-9/_-]+$")
    
class CheckResponse(BaseModel):
    allowed: bool
    remaining: int
    reset_at: datetime

@app.post("/limits")
async def create_limit(config: LimitConfigRequest):
    limits_db[config.endpoint] = config
    return config

@app.get("/limits/{endpoint:path}")
async def get_limit(endpoint: str):
    if not endpoint.startswith('/'):
        endpoint = f"/{endpoint}"
        
    if endpoint not in limits_db:
        raise HTTPException(status_code=404, detail="Limit not found")
    
    return limits_db[endpoint]

@app.post('/check', response_model=CheckResponse)
async def check_rate_limit(req: CheckRequest):
    if req.endpoint not in limits_db:
        raise HTTPException(status_code=404, detail="Endpoint not figured")
    
    config = limits_db[req.endpoint]
    now = time.time()
    
    window_start = (now // config.window_seconds) * config.window_seconds
    reset_at = datetime.fromtimestamp(window_start + config.window_seconds)
    
    endpoint_storage = requests_db.setdefault(req.endpoint, {})
    
    user_state = requests_db.setdefault(req.endpoint, {}).get(
        req.user_id, {"count": 0, "window_start": window_start}
    )
    
    if user_state["window_start"] < window_start:
        user_state = {"count": 0, "window_start": window_start}
    
    allowed = False
    
    if user_state["count"] < config.max_requests:
        user_state["count"] += 1
        allowed = True
    
    endpoint_storage[req.user_id] = user_state
    remaining = max(0, config.max_requests - user_state["count"])
    
    print(f"Rate limit check: {req.endpoint} for user {req.user_id} = {allowed} ({remaining} remaining)")
    
    return {
        "allowed": allowed,
        "remaining": max(0, remaining),
        "reset_at": reset_at
    }
    
    
        
    
