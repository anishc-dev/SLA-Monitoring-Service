from fastapi import FastAPI, Request
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional
import uuid
from DB.database import get_all_tickets, init_db, create_ticket_db, get_ticket_by_id, get_dashboard_data
from fastapi.responses import HTMLResponse
from logger import set_correlation_id, error, set_operation, set_ticket_id, info

app = FastAPI(title="SLA Monitor API",description="API for listening to ticket creation")

init_db()

class TicketValidator(BaseModel):
    id: Optional[int] = Field(default=0)
    priority: Optional[str] = Field(default="low")
    status: Optional[str] = Field(default="open")
    created_at: Optional[str] = Field(default_factory= lambda: datetime.now(timezone.utc).isoformat())
    updated_at: Optional[str] = Field(default_factory= lambda: datetime.now(timezone.utc).isoformat())
    customer_tier: Optional[str] = Field(default="P0")

def ticket_validator(ticket: TicketValidator):
    set_operation("ticket_validation")
    set_ticket_id(str(ticket.id))
    
    if ticket.id is None or ticket.id < 0:
        error("Ticket ID validation failed", ticket_id=ticket.id, reason="ID must be greater than 0")
        return {"error": "Ticket ID must be greater than 0."}
    if ticket.priority not in ["low", "medium", "high"]:
        error("Ticket priority validation failed", ticket_id=ticket.id, priority=ticket.priority)
        return {"error": "Invalid priority. Must be 'low', 'medium', or 'high'"}
    if ticket.status not in ["open", "in_progress", "closed"]:
        error("Ticket status validation failed", ticket_id=ticket.id, status=ticket.status)
        return {"error": "Invalid status. Must be 'open', 'in_progress', or 'closed'."}
    if ticket.customer_tier not in ["P0", "P1", "P2", "P3"]:
        error("Ticket customer tier validation failed", ticket_id=ticket.id, customer_tier=ticket.customer_tier)
        return {"error": "Invalid customer tier. Must be 'P0', 'P1', 'P2', or 'P3'."}
    if ticket.created_at and ticket.updated_at and ticket.created_at > ticket.updated_at:
        error("Ticket timestamp validation failed", ticket_id=ticket.id, created_at=ticket.created_at, updated_at=ticket.updated_at)
        return {"error": "Created at must be before updated at."}
    
    info("Ticket validation successful", ticket_id=ticket.id)
    return {"status": "success"}

def log_ticket_creation(db_result, ticket_dict):
    set_operation("ticket_creation_logging")
    set_ticket_id(str(ticket_dict.get("id", "")))
    
    if db_result.get("status") == "CREATED":
        info("Ticket creation logged", ticket_id=ticket_dict["id"], status="CREATED")
        return {"received": ticket_dict, "status": "CREATED", "message": "Ticket CREATED successfully"}
    elif db_result.get("status") == "UPDATED":
        info("Ticket update logged", ticket_id=ticket_dict["id"], status="UPDATED")
        return {"received": ticket_dict, "status": "UPDATED", "message": "Ticket UPDATED successfully"}
    else:
        error("Ticket creation error logged", ticket_id=ticket_dict["id"], status="ERROR")
        return {"received": ticket_dict, "status": "ERROR", "message": "Ticket ERROR"}


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    try:
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        set_correlation_id(correlation_id)
        info("Request received", correlation_id=correlation_id, path=request.url.path, method=request.method)
        response = await call_next(request)
    except Exception as e:
        error("Error adding correlation ID", error=str(e))
        raise
    return response

@app.post("/tickets")
async def create_ticket(ticket: TicketValidator):
    try:
        set_operation("ticket_creation_endpoint")
        set_ticket_id(str(ticket.id))   
    
        if isinstance(ticket, list):
            set_operation("batch_ticket_creation")
            info("Processing batch ticket creation", ticket_count=len(ticket))
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
    except Exception as e:
        error("Error creating ticket", error=str(e), ticket_id=str(ticket.id))
        raise

@app.get("/")
def read_root():
    set_operation("api_root_access")
    set_correlation_id(str(uuid.uuid4()))
    info("API root endpoint accessed")
    return {"message": "Welcome to the Ticket Listener API"}

@app.get("/tickets/{id}")
async def get_tickets_by_id(id: int):
    """
    Get ticket by ID
    """
    try:
        set_operation("ticket_retrieval_endpoint")
        set_ticket_id(str(id))
        info("Ticket retrieval request", ticket_id=id)
        ticket = get_ticket_by_id(id)
        if ticket:
            info("Ticket retrieved successfully", ticket_id=id)
        else:
            info("Ticket not found", ticket_id=id)
        return {"received": ticket, "status": "SUCCESS", "message": "Ticket SUCCESS"}
    except Exception as e:
        error("Error retrieving ticket by ID", error=str(e), ticket_id=id)
        raise

@app.get("/dashboard")
async def get_dashboard():
    """
    Get dashboard data as HTML
    """
    try:
        set_operation("dashboard_endpoint")
        set_correlation_id(str(uuid.uuid4()))
        info("Dashboard request received")
        dashboard_data = sorted(get_dashboard_data(), key=lambda x: x[0])
        headers = ["ID", "Priority", "Status", "Created At", "Updated At", "Customer Tier", "Escalation Level", "Elapsed %", "Elapsed Sec"]
        html = "<html><head><title>SLA Dashboard</title></head><body>"
        html += "<h2>SLA Dashboard</h2>"
        html += "<table border='1' cellpadding='5' style='border-collapse:collapse;'>"
        html += "<tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>"
        for row in dashboard_data:
            html += "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
        html += "</table></body></html>"
        
        info("Dashboard data retrieved", ticket_count=len(dashboard_data))
        return HTMLResponse(content=html)
    except Exception as e:
        error("Error generating dashboard HTML", error=str(e))
        error_html = f"<html><head><title>Dashboard Error</title></head><body><h2>Dashboard \
                        Error</h2><p>An error occurred while generating the dashboard: \
                        {str(e)}</p></body></html>"
        return HTMLResponse(content=error_html, status_code=500)