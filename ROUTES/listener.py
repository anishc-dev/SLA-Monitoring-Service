from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional, List
import uuid
import json
from DB.database import get_all_tickets, init_db, create_ticket_db, get_ticket_by_id, get_dashboard_data
from fastapi.responses import HTMLResponse
from logger import set_correlation_id, error, set_operation, set_ticket_id, info, start_timer
import psycopg2
import os
from jinja2 import Environment, FileSystemLoader

def get_db():
    return psycopg2.connect(os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/sla_monitor"))

app = FastAPI(title="SLA Monitor API",description="API for listening to ticket creation")

template_env = Environment(loader=FileSystemLoader("templates"))

init_db()

# Minimal WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

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
        start_timer()
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        set_correlation_id(correlation_id)
        info("Request received", correlation_id=correlation_id, path=request.url.path, method=request.method)
        
        response = await call_next(request)

        info("Request completed", correlation_id=correlation_id, path=request.url.path, method=request.method, status_code=response.status_code)
        
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
async def get_dashboard(page: int = 1, filter: str = "all"):
    """
    Get dashboard data as HTML with pagination and filtering
    """
    try:
        start_timer()
        set_operation("dashboard_endpoint")
        set_correlation_id(str(uuid.uuid4()))
        info("Dashboard request received", page=page, filter=filter)
        dashboard_data = sorted(get_dashboard_data(), key=lambda x: x[0])
        
        # Apply breach filter
        if filter == "breach":
            dashboard_data = [row for row in dashboard_data if len(row) > 6 and row[6] == "BREACH"]
        elif filter == "alert":
            dashboard_data = [row for row in dashboard_data if len(row) > 6 and row[6] == "ALERT"]
        
        # Pagination
        page_size = 10
        total_pages = (len(dashboard_data) + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_data = dashboard_data[start_idx:end_idx]
        
        # Calculate relative times for each row
        current_time = datetime.now(timezone.utc)
        processed_data = []
        
        for row in paginated_data:
            try:
                # Parse created_at and updated_at timestamps
                created_at_str = row[3] if len(row) > 3 else ""
                updated_at_str = row[4] if len(row) > 4 else ""
                
                # Calculate relative times
                created_relative = "N/A"
                updated_relative = "N/A"
                
                if created_at_str:
                    try:
                        created_dt = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                        created_diff = current_time - created_dt
                        created_relative = format_relative_time(created_diff)
                    except:
                        created_relative = "Invalid"
                
                if updated_at_str:
                    try:
                        updated_dt = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
                        updated_diff = current_time - updated_dt
                        updated_relative = format_relative_time(updated_diff)
                    except:
                        updated_relative = "Invalid"
                
                # Create new row with relative times
                new_row = list(row)
                new_row.insert(4, created_relative)  # Insert after "Created At"
                new_row.insert(6, updated_relative)  # Insert after "Updated At"
                processed_data.append(new_row)
                
            except Exception as e:
                # If there's an error processing a row, keep the original
                error("Error processing dashboard row", error=str(e), row_data=row)
                processed_data.append(list(row) + ["Error", "Error"])
        
        headers = ["ID", "Priority", "Status", "Created At", "Created", "Updated At", "Updated", "Customer Tier", "Escalation Level", "Elapsed %", "Elapsed Sec"]
        
        # Render template with data
        template = template_env.get_template("dashboard.html")
        html = template.render(
            current_time=current_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            headers=headers,
            processed_data=processed_data,
            page=page,
            total_pages=total_pages,
            filter=filter,
            total_count=len(dashboard_data)
        )
        
        info("Dashboard data retrieved", ticket_count=len(processed_data), total_count=len(dashboard_data), page=page, filter=filter)
        return HTMLResponse(content=html)
    except Exception as e:
        error("Error generating dashboard HTML", error=str(e))
        error_html = f"<html><head><title>Dashboard Error</title></head><body><h2>Dashboard \
                        Error</h2><p>An error occurred while generating the dashboard: \
                        {str(e)}</p></body></html>"
        return HTMLResponse(content=error_html, status_code=500)

def format_relative_time(timedelta_obj):
    """
    Format a timedelta object into a human-readable relative time string
    """
    total_seconds = int(timedelta_obj.total_seconds())
    
    if total_seconds < 0:
        return "Future"
    
    if total_seconds < 60:
        return f"{total_seconds}s ago"
    
    minutes = total_seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    
    days = hours // 24
    if days < 30:
        return f"{days}d ago"
    
    months = days // 30
    if months < 12:
        return f"{months}mo ago"
    
    years = months // 12
    return f"{years}y ago"

@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def broadcast_alert(alert_data):
    await manager.broadcast(json.dumps(alert_data))

@app.post("/broadcast-alert")
async def trigger_broadcast(alert_data: dict):
    """
    HTTP endpoint to trigger WebSocket broadcast from scheduler
    """
    try:
        await manager.broadcast(json.dumps(alert_data))
        info(f"WebSocket broadcast triggered via HTTP for ticket {alert_data.get('ticket_id')}")
        return {"status": "success", "message": "Alert broadcasted"}
    except Exception as e:
        error(f"HTTP broadcast error: {e}")
        return {"status": "error", "message": str(e)}

@app.delete("/clear")
async def clear_database(ticket_id: Optional[int] = None):
    """
    Clear database: 
    - No ticket_id: Clear all tickets and alerts
    - With ticket_id: Clear specific ticket and its alerts
    """
    try:
        set_operation("clear_database_endpoint")
        set_correlation_id(str(uuid.uuid4()))
        
        conn = get_db()
        cur = conn.cursor()
        
        if ticket_id:
            cur.execute("DELETE FROM tickets WHERE id = %s", (ticket_id,))
            tickets_deleted = cur.rowcount
            cur.execute("DELETE FROM sla_breach_alerts WHERE ticket_id = %s", (ticket_id,))
            alerts_deleted = cur.rowcount
            info(f"Cleared ticket {ticket_id}", tickets_deleted=tickets_deleted, alerts_deleted=alerts_deleted)
        else:
            cur.execute("DELETE FROM tickets")
            tickets_deleted = cur.rowcount
            cur.execute("DELETE FROM sla_breach_alerts")
            alerts_deleted = cur.rowcount
            info("Cleared all tickets and alerts", tickets_deleted=tickets_deleted, alerts_deleted=alerts_deleted)
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {
            "status": "SUCCESS",
            "message": f"Cleared {'ticket ' + str(ticket_id) if ticket_id else 'all tickets'}",
            "tickets_deleted": tickets_deleted,
            "alerts_deleted": alerts_deleted
        }
        
    except Exception as e:
        error("Error clearing database", error=str(e))
        return {"status": "ERROR", "message": str(e)}