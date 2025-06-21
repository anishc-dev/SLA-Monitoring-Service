from fastapi import FastAPI, Request
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional

app = FastAPI(title="SLA Monitor API",description="API for listening to ticket creation")

ticket_db = {}

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

@app.post("/tickets")
async def create_ticket(ticket: TicketValidator):
    """
    Ingest ticket data
    """
    status = ticket_validator(ticket)
    if status.get("status") != "success":
        return status

    ticket_dict = ticket.model_dump()
    
    # idempotency by id + updated_at
    for stored_id, stored_ticket in ticket_db.items():
        if stored_ticket["id"] == ticket.id and stored_ticket["updated_at"] == ticket.updated_at:
            print(f"Ticket already exists. Updating ticket ID {ticket.id}")
            ticket_db[stored_id] = ticket_dict
            return {"received": ticket_dict, "status": "updated"}

    ticket_db[ticket.id] = ticket_dict
    print(f"Stored new ticket with ID {ticket.id}. Total tickets: {len(ticket_db)}")
    return {"received": ticket_dict, "status": "success"}

@app.get("/tickets")
async def get_tickets():
    """Get all tickets"""
    tickets_list = list(ticket_db.values())
    print(f"Returning {len(tickets_list)} tickets from database")
    print(f"Database keys: {list(ticket_db.keys())}")
    return {"tickets": tickets_list, "count": len(ticket_db)}

@app.get("/tickets/{ticket_id}")
async def get_ticket_by_id(ticket_id: int):
    """Get ticket by ID"""
    if ticket_id in ticket_db:
        return {"ticket": ticket_db[ticket_id]}
    return {"error": f"Ticket with ID {ticket_id} not found"}

@app.get("/debug")
async def debug_info():
    """Debug endpoint to see what's in the database"""
    return {
        "ticket_db_keys": list(ticket_db.keys()),
        "ticket_db_values": list(ticket_db.values()),
        "ticket_db_type": str(type(ticket_db)),
        "ticket_db_length": len(ticket_db)
    }

@app.get("/")
def read_root():
    return {"message": "Welcome to the Ticket Listener API"}

