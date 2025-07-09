#!/usr/bin/env python3
"""
Simple test for Railway deployment
"""

import os
import logging
from fastapi import FastAPI
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello from Railway!", "version": "test-1.0"}


@app.get("/api/version")
async def version():
    return {"version": "test-1.0", "deployment": "railway-test"}


@app.get("/api/test")
async def test():
    return {"status": "working", "files": os.listdir(".")}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting test server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
