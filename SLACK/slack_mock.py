from fastapi import FastAPI, Request
import uvicorn
import logging
import sys
import os

sys.path.append('/app')
from logger import info, set_operation, set_correlation_id
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.post("/slack/events")
async def slack_events(request: Request):
    set_operation("slack_mock_event_reception")
    set_correlation_id(str(uuid.uuid4()))
    data = await request.json()
    info("Slack event received", event_data=data)
    return {"status": "success", "message": "Slack events received"}

@app.get("/")
async def root():
    set_operation("slack_mock_health_check")
    set_correlation_id(str(uuid.uuid4()))
    info("Slack mock health check endpoint accessed")
    return {"message": "Slack Mock Server is running"}

if __name__ == "__main__":
    set_operation("slack_mock_server_startup")
    logger.info("Starting Slack Mock Server on port 5000")
    info("Slack Mock Server starting up", port=5000)
    uvicorn.run(app, host="0.0.0.0", port=5000)
