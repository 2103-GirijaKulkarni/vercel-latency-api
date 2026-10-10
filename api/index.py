import json
from pathlib import Path

import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# Enable CORS for POST requests from any origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

DATA_FILE = Path(__file__).parent / "q-vercel-latency.json"

with open(DATA_FILE, "r") as f:
    raw_data = json.load(f)

# Handles either a top-level JSON list or {"telemetry": [...]}.
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