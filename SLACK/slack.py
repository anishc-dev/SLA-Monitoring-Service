import os
import requests
from logger import info, error

def send_slack_message(message, ticket_id):
    """
    Send a message to a Slack channel.
    """

    slack_URL = os.getenv('SLACK_URL')
    if not slack_URL:
        return {"status": "error", "message": "SLACK_URL is not set"}
    slack_message = {
        "text": message
    }
    try:
        response = requests.post(slack_URL, json=slack_message)
        if response.status_code == 200:
            info("Slack message sent successfully", ticket_id=ticket_id)
            return {"status": "success", "message": "Slack message sent successfully", "response": response.text}
        else:
            error("Error sending slack message", ticket_id=ticket_id, status_code=response.status_code)
            return {"status": "error", "message": "Error sending slack message", "response": response.text}
    except requests.exceptions.RequestException as e:
        error("Error sending slack message - RequestException", ticket_id=ticket_id, error=str(e))
        return {"status": "exception", "message": "Error sending slack message", "response": str(e) }
    except Exception as e:
        error("Error sending slack message - Exception", ticket_id=ticket_id, error=str(e))
        return {"status": "exception", "message": "Error sending slack message", "response": str(e) }

def slack_message_sender(ticket, remaining_time):
    """
    Messaging for slack channel
    """
    message = f"Ticket ID: {ticket['id']}\n"
    message += f"Ticket Priority: {ticket['priority'].upper()}\n"
    message += f"Ticket Tier: {ticket['customer_tier'].upper()}\n"
    message += f"Ticket Created At: {ticket['created_at']}\n"
    message += f"Ticket Updated At: {ticket['updated_at']}\n"
    message += f"Ticket Status: {ticket['status'].upper()}\n"
    message += f"Ticket Remaining Time: {remaining_time} seconds\n"
    
    return send_slack_message(message, ticket['id'])
