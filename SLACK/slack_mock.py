from fastapi import FastAPI, Request
import uvicorn
import logging
import sys
import os
import requests
import uuid

sys.path.append('/app')

from logger import info, error, set_operation, set_correlation_id, set_ticket_id, start_timer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.post("/slack/events")
async def slack_events(request: Request):
    start_timer()
    set_operation("slack_mock_event_reception")
    set_correlation_id(str(uuid.uuid4()))
    data = await request.json()
    info("Slack event received", event_data=data)
    return {"status": "success", "message": "Slack events received"}

@app.get("/")
async def root():
    start_timer()
    set_operation("slack_mock_health_check")
    set_correlation_id(str(uuid.uuid4()))
    info("Slack mock health check endpoint accessed")
    return {"message": "Slack Mock Server is running"}

def send_slack_message(message, ticket_id):
    """
    Send a message to a Slack channel.
    """
    start_timer()
    set_operation("slack_mock_message_send")
    set_ticket_id(str(ticket_id))

    slack_URL = os.getenv('SLACK_URL')
    if not slack_URL:
        error("SLACK_URL environment variable not set", ticket_id=ticket_id)
        return {"status": "error", "message": "SLACK_URL is not set"}
    slack_message = {
        "text": message
    }
    try:
        response = requests.post(slack_URL, json=slack_message)
        if response.status_code == 200:
            info("Slack mock message sent successfully", ticket_id=ticket_id)
            return {"status": "success", "message": "Slack mock message sent successfully", "response": response.text}
        else:
            error("Error sending slack mock message", ticket_id=ticket_id, status_code=response.status_code)
            return {"status": "error", "message": "Error sending slack mock message", "response": response.text}
    except requests.exceptions.RequestException as e:
        error("Error sending slack mock message - RequestException", ticket_id=ticket_id, error=str(e))
        return {"status": "exception", "message": "Error sending slack mock message", "response": str(e) }
    except Exception as e:
        error("Error sending slack mock message - Exception", ticket_id=ticket_id, error=str(e))
        return {"status": "exception", "message": "Error sending slack mock message", "response": str(e) }

def slack_message_sender(ticket, remaining_time):
    """
    Messaging for slack channel
    """
    start_timer()
    set_operation("slack_mock_message_preparation")
    set_ticket_id(str(ticket.get('id', '')))
    
    message = f"Ticket ID: {ticket['id']}\n"
    message += f"Ticket Priority: {ticket['priority'].upper()}\n"
    message += f"Ticket Tier: {ticket['customer_tier'].upper()}\n"
    message += f"Ticket Created At: {ticket['created_at']}\n"
    message += f"Ticket Updated At: {ticket['updated_at']}\n"
    message += f"Ticket Status: {ticket['status'].upper()}\n"
    message += f"Ticket Remaining Time: {remaining_time} seconds\n"
    
    info("Slack mock message prepared", ticket_id=ticket['id'], message_length=len(message))
    return send_slack_message(message, ticket['id'])

if __name__ == "__main__":
    start_timer()
    set_operation("slack_mock_server_startup")
    logger.info("Starting Slack Mock Server on port 5000")
    info("Slack Mock Server starting up", port=5000)
    uvicorn.run(app, host="0.0.0.0", port=5000)
