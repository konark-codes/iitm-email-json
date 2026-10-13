"""Redis-backed counter API for the Compose assignment."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from redis.asyncio import Redis

REDIS_URL = "redis://redis:6379/0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = Redis.from_url(REDIS_URL, decode_responses=True)
    await client.ping()
    app.state.redis = client
    try:
        yield
    finally:
        await client.aclose()


app = FastAPI(lifespan=lifespan)


def validate_key(key: str) -> str:
    if not key:
        raise HTTPException(status_code=400, detail="key must not be empty")
    return key


@app.post("/hit/{key}")
async def hit(key: str) -> dict[str, int | str]:
    key = validate_key(key)
    # Redis INCR is atomic, including under concurrent requests.
    count = await app.state.redis.incr(f"counter:{key}")
    return {"key": key, "count": count}


@app.get("/count/{key}")
async def count(key: str) -> dict[str, int | str]:
    key = validate_key(key)
    value = await app.state.redis.get(f"counter:{key}")
    return {"key": key, "count": int(value) if value is not None else 0}


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    try:
        if not await app.state.redis.ping():
            raise RuntimeError("Redis ping failed")
    except Exception as exc:
        raise HTTPException(status_code=503, detail="redis unavailable") from exc
    return {"status": "ok", "redis": "up"}
