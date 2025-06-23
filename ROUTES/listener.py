from fastapi import FastAPI, Request
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional
from DB.database import get_all_tickets, init_db, create_ticket_db, get_ticket_by_id, get_dashboard_data

app = FastAPI(title="SLA Monitor API",description="API for listening to ticket creation")

init_db()

class TicketValidator(BaseModel):
    id: Optional[int] = Field(default=0)
    priority: Optional[str] = Field(default="low")
    status: Optional[str] = Field(default="open")
    created_at: Optional[str] = Field(default=datetime.now(timezone.utc).isoformat())
    updated_at: Optional[str] = Field(default=datetime.now(timezone.utc).isoformat())
    customer_tier: Optional[str] = Field(default="P0")

def ticket_validator(ticket: TicketValidator):
    
    if ticket.id is None or ticket.id < 0:
        return {"error": "Ticket ID must be greater than 0."}
    if ticket.priority not in ["low", "medium", "high"]:
        return {"error": "Invalid priority. Must be 'low', 'medium', or 'high'"}
    if ticket.status not in ["open", "in_progress", "closed"]:
        return {"error": "Invalid status. Must be 'open', 'in_progress', or 'closed'."}
    if ticket.customer_tier not in ["P0", "P1", "P2", "P3"]:
        return {"error": "Invalid customer tier. Must be 'P0', 'P1', 'P2', or 'P3'."}
    if ticket.created_at and ticket.updated_at and ticket.created_at > ticket.updated_at:
        return {"error": "Created at must be before updated at."}
    
    return {"status": "success"}

def log_ticket_creation(db_result, ticket_dict):
    if db_result.get("status") == "CREATED":
        return {"received": ticket_dict, "status": "CREATED", "message": "Ticket CREATED successfully"}
    elif db_result.get("status") == "UPDATED":
        return {"received": ticket_dict, "status": "UPDATED", "message": "Ticket UPDATED successfully"}
    else:
        return {"received": ticket_dict, "status": "ERROR", "message": "Ticket ERROR"}

@app.post("/tickets")
async def create_ticket(ticket: TicketValidator):

    if isinstance(ticket, list):
        for t in ticket:
            status = ticket_validator(t)
            if status.get("status") != "success":
                return status
            ticket_dict = t.model_dump()
            db_result = create_ticket_db(ticket_dict)
            return log_ticket_creation(db_result, ticket_dict)

    status = ticket_validator(ticket)
    if status.get("status") != "success":
        return status

    ticket_dict = ticket.model_dump()
    db_result = create_ticket_db(ticket_dict)
    return log_ticket_creation(db_result, ticket_dict)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Ticket Listener API"}

@app.get("/tickets/{id}")
async def get_tickets_by_id(id: int):
    """
    Get ticket by ID
    """
    ticket = get_ticket_by_id(id)
    return {"received": ticket, "status": "SUCCESS", "message": "Ticket SUCCESS"}

@app.get("/dashboard")
async def get_dashboard():
    """
    Get dashboard data
    """
    dashboard_data = get_dashboard_data()
    return {"received": dashboard_data, "status": "SUCCESS", "message": "Dashboard SUCCESS"}