import json
from pathlib import Path

import numpy as np
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Expose-Headers": "Access-Control-Allow-Origin",
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["Access-Control-Allow-Origin"],
)


@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    response = await call_next(request)
    for header, value in CORS_HEADERS.items():
        response.headers[header] = value
    return response


@app.options("/")
def options_handler(response: Response):
    for header, value in CORS_HEADERS.items():
        response.headers[header] = value
    response.status_code = 204
    return response


DATA_FILE = Path(__file__).parent / "q-vercel-latency.json"

with open(DATA_FILE, "r", encoding="utf-8") as f:
    raw_data = json.load(f)

if isinstance(raw_data, list):
    TELEMETRY = raw_data
else:
    TELEMETRY = []
    for value in raw_data.values():
        if isinstance(value, list):
            TELEMETRY = value
            break


class AnalyticsRequest(BaseModel):
    regions: list[str]
    threshold_ms: float


@app.post("/")
def analytics(body: AnalyticsRequest):
    result = {}

    for region in body.regions:
        records = [
            record
            for record in TELEMETRY
            if record.get("region") == region
        ]

        latencies = [float(record["latency_ms"]) for record in records]
        uptimes = [float(record["uptime_pct"]) for record in records]

        result[region] = {
            "avg_latency": float(np.mean(latencies)),
            "p95_latency": float(np.percentile(latencies, 95)),
            "avg_uptime": float(np.mean(uptimes)),
            "breaches": sum(
                1 for latency in latencies if latency > body.threshold_ms
            ),
        }

    return result
