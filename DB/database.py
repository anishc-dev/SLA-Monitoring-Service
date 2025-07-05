import psycopg2
import os
from logger import error, info, set_correlation_id, set_operation, set_ticket_id, start_timer

def get_db():
    return psycopg2.connect(os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/sla_monitor"))

def create_table_if_not_exists(table_name, columns, primary_key):
    start_timer()
    set_operation("database_table_creation")
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns}, PRIMARY KEY ({primary_key}))")
    conn.commit()
    cur.close()
    conn.close()
    info("Table created", table_name=table_name)

def init_db():
    start_timer()
    set_operation("database_initialization")
    #one table for alerts and tickets
    create_table_if_not_exists(
        "tickets", "id INTEGER, priority VARCHAR(10), status VARCHAR(20), created_at VARCHAR(50), updated_at VARCHAR(50), \
         customer_tier VARCHAR(10), escalation_level VARCHAR(10), elapsed_time_percentage INTEGER, elapsed_time_seconds INTEGER", "id")
    #one table for alerts
    create_table_if_not_exists("sla_breach_alerts", "id SERIAL, ticket_id INTEGER, priority VARCHAR(10), status VARCHAR(20), \
        created_at VARCHAR(50), updated_at VARCHAR(50), customer_tier VARCHAR(10), elapsed_time_seconds INTEGER, elapsed_time_percentage INTEGER, \
        escalation_level VARCHAR(10)", "id")
    info("Database initialization completed")

def create_ticket_db(ticket_data):
    """
    Database operation to create or update a ticket in the DB
    if the ticket already exists, it will be updated
    if the ticket does not exist, it will be created
    """
    start_timer()
    set_operation("ticket_creation_db")
    set_ticket_id(str(ticket_data.get("id", "")))
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT * FROM tickets WHERE id = %s AND updated_at = %s
    """, (ticket_data["id"], ticket_data["updated_at"]))
    
    if cur.fetchone(): #code to fetch tickets if exists
        cur.execute("""
            UPDATE tickets 
            SET priority=%s, status=%s, created_at=%s, customer_tier=%s
            WHERE id=%s AND updated_at=%s
        """, (ticket_data["priority"], ticket_data["status"], 
                ticket_data["created_at"], ticket_data["customer_tier"],
                ticket_data["id"], ticket_data["updated_at"]))
        conn.commit()
        info("Ticket updated in database", ticket_id=ticket_data["id"])
        return {"status": "UPDATED"}

    #code to create tickets if not exists
    cur.execute("""
        INSERT INTO tickets (id, priority, status, created_at, updated_at, customer_tier)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (ticket_data["id"], ticket_data["priority"], ticket_data["status"], 
            ticket_data["created_at"], ticket_data["updated_at"], ticket_data["customer_tier"]))
    conn.commit()
    info("Ticket created in database", ticket_id=ticket_data["id"])
    return {"status": "CREATED"}
        
    
def get_all_tickets(open=None):
    """
    get all open tickets from the DB if open is True
    get all tickets from the DB if open is False
    """
    start_timer()
    set_operation("ticket_retrieval_all")
    conn = get_db()
    cur = conn.cursor()
    if open:
        cur.execute("""
            SELECT * FROM tickets WHERE status = 'open'
        """)
        info("Retrieved open tickets from database")
    else:
        cur.execute("""
            SELECT * FROM tickets
        """)
        info("Retrieved all tickets from database")
    tickets = cur.fetchall()
    cur.close()
    conn.close()
    tickets_json = {}
    for ticket in tickets:
        tickets_json[ticket[0]] = {
            "id": ticket[0],
            "priority": ticket[1],
            "status": ticket[2],
            "created_at": ticket[3],
            "updated_at": ticket[4],
            "customer_tier": ticket[5]
        }
    info("All tickets processed", ticket_count=len(tickets_json))
    return tickets_json

def get_ticket_by_id(id):
    start_timer()
    set_operation("ticket_retrieval_by_id")
    set_ticket_id(str(id))
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM tickets WHERE id = %s
    """, (id,))
    ticket = cur.fetchone()
    cur.close() 
    conn.close()
    if ticket:
        info("Ticket retrieved by ID", ticket_id=id)
    else:
        info("Ticket not found by ID", ticket_id=id)
    return ticket

def get_dashboard_data():
    start_timer()
    set_operation("dashboard_data_retrieval")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM tickets
    """)
    dashboard_data = cur.fetchall()
    cur.close()
    conn.close()
    info("Dashboard data retrieved", record_count=len(dashboard_data))
    return dashboard_data

def create_sla_breach_alert_db(ticket_data, elapsed_time_seconds, elapsed_time_percentage, escalation_level):
    start_timer()
    set_operation("sla_breach_alert_creation")
    set_ticket_id(str(ticket_data.get("id", "")))
    conn = get_db()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT id FROM sla_breach_alerts 
            WHERE ticket_id = %s AND escalation_level = %s
        """, (ticket_data["id"], escalation_level))
        
        if cur.fetchone():
            info("Alert already exists", ticket_id=ticket_data["id"], escalation_level=escalation_level)
            return {"status": "EXISTS"}
        
        cur.execute("""
            INSERT INTO sla_breach_alerts (ticket_id, priority, status, created_at, updated_at, customer_tier, \
            elapsed_time_seconds, elapsed_time_percentage, escalation_level)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (ticket_data["id"], ticket_data["priority"], ticket_data["status"], ticket_data["created_at"],
         ticket_data["updated_at"], ticket_data["customer_tier"], int(elapsed_time_seconds), int(elapsed_time_percentage), escalation_level))
        conn.commit()

        cur.execute("""
            UPDATE tickets
            SET escalation_level = %s,
                elapsed_time_percentage = %s,
                elapsed_time_seconds = %s
            WHERE id = %s
        """, (escalation_level, int(elapsed_time_percentage), int(elapsed_time_seconds), ticket_data["id"]))
        conn.commit()

        info("SLA breach alert created", ticket_id=ticket_data["id"], escalation_level=escalation_level)
        return {"status": "CREATED"}
        
    except Exception as e:
        error("Database error in create_sla_breach_alert_db", error=str(e), ticket_id=ticket_data.get("id"))
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()
        conn.close()

def update_sla_breach_alert_db(ticket_data, elapsed_time_seconds, elapsed_time_percentage, escalation_level):
    start_timer()
    set_operation("sla_breach_alert_update")
    set_ticket_id(str(ticket_data.get("id", "")))
    conn = get_db()
    cur = conn.cursor()
    
    try:
        # Check if a record exists for this ticket and escalation level
        cur.execute("""
            SELECT id FROM sla_breach_alerts 
            WHERE ticket_id = %s AND escalation_level = %s
        """, (ticket_data["id"], escalation_level))
        
        existing_record = cur.fetchone()
        
        if existing_record:
            # Update existing record
            cur.execute("""
                UPDATE sla_breach_alerts 
                SET elapsed_time_seconds = %s, elapsed_time_percentage = %s 
                WHERE ticket_id = %s AND escalation_level = %s
            """, (int(elapsed_time_seconds), int(elapsed_time_percentage), ticket_data["id"], escalation_level))
            conn.commit()

            cur.execute("""
                UPDATE tickets
                SET escalation_level = %s,
                    elapsed_time_percentage = %s,
                    elapsed_time_seconds = %s
                WHERE id = %s
            """, (escalation_level, int(elapsed_time_percentage), int(elapsed_time_seconds), ticket_data["id"]))
            conn.commit()
            info("SLA breach alert updated", ticket_id=ticket_data["id"], escalation_level=escalation_level)
            return {"status": "UPDATED"}
        else:
            # Create new record if none exists
            info("Alert does not exist, creating new one", ticket_id=ticket_data["id"], escalation_level=escalation_level)
            cur.execute("""
                INSERT INTO sla_breach_alerts (ticket_id, priority, status, created_at, updated_at, customer_tier, \
                elapsed_time_seconds, elapsed_time_percentage, escalation_level)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (ticket_data["id"], ticket_data["priority"], ticket_data["status"], ticket_data["created_at"],
             ticket_data["updated_at"], ticket_data["customer_tier"], int(elapsed_time_seconds), int(elapsed_time_percentage), escalation_level))
            conn.commit()

            cur.execute("""
                UPDATE tickets
                SET escalation_level = %s,
                    elapsed_time_percentage = %s,
                    elapsed_time_seconds = %s
                WHERE id = %s
            """, (escalation_level, int(elapsed_time_percentage), int(elapsed_time_seconds), ticket_data["id"]))
            conn.commit()
            info("SLA breach alert created during update", ticket_id=ticket_data["id"], escalation_level=escalation_level)
            return {"status": "CREATED"}
            
    except Exception as e:
        error("Database error in update_sla_breach_alert_db", error=str(e), ticket_id=ticket_data.get("id"))
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()
        conn.close()



