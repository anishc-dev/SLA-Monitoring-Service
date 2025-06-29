from fastapi import FastAPI, Request
import uvicorn
import logging
import sys
import os

sys.path.append('/app')
from logger import info

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.post("/slack/events")
async def slack_events(request: Request):
    data = await request.json()
    info("Slack event received", event_data=data)
    return {"status": "success", "message": "Slack events received"}

@app.get("/")
async def root():
    return {"message": "Slack Mock Server is running"}

if __name__ == "__main__":
    logger.info("Starting Slack Mock Server on port 5000")
    uvicorn.run(app, host="0.0.0.0", port=5000)
