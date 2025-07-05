import os
import requests
from logger import info, error, set_operation, set_ticket_id, start_timer
import aiohttp

async def send_slack_message(message, ticket_id):
    """
    Send a message to a Slack channel.
    """
    start_timer()
    set_operation("slack_message_send")
    set_ticket_id(str(ticket_id))

    slack_URL = os.getenv('SLACK_URL')
    if not slack_URL:
        error("SLACK_URL environment variable not set", ticket_id=ticket_id)
        return {"status": "error", "message": "SLACK_URL is not set"}
    slack_message = {
        "text": message
    }
    
    async with aiohttp.ClientSession() as session:
        response = await session.post(slack_URL, json=slack_message)
    if response.status_code == 200:
        info("Slack message sent successfully", ticket_id=ticket_id)
        return {"status": "success", "message": "Slack message sent successfully", "response": response.text}
    else:
        error("Error sending slack message", ticket_id=ticket_id, status_code=response.status_code)
        return {"status": "error", "message": "Error sending slack message", "response": response.text}
   

async def slack_message_sender(ticket, remaining_time):
    """
    Messaging for slack channel
    """
    start_timer()
    set_operation("slack_message_preparation")
    set_ticket_id(str(ticket.get('id', '')))
    
    message = f"Ticket ID: {ticket['id']}\n"
    message += f"Ticket Priority: {ticket['priority'].upper()}\n"
    message += f"Ticket Tier: {ticket['customer_tier'].upper()}\n"
    message += f"Ticket Created At: {ticket['created_at']}\n"
    message += f"Ticket Updated At: {ticket['updated_at']}\n"
    message += f"Ticket Status: {ticket['status'].upper()}\n"
    message += f"Ticket Remaining Time: {remaining_time} seconds\n"
    
    info("Slack message prepared", ticket_id=ticket['id'], message_length=len(message))
    return await send_slack_message(message, ticket['id'])
