import psycopg2
import os

def get_db():
    return psycopg2.connect(os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/sla_monitor"))

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY,
            priority VARCHAR(10),
            status VARCHAR(20),
            created_at VARCHAR(50),
            updated_at VARCHAR(50),
            customer_tier VARCHAR(10)
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def create_ticket_db(ticket_data):
    conn = get_db()
    cur = conn.cursor()
    
    try:
        # Check for idempotency - same id and updated_at
        cur.execute("""
            SELECT * FROM tickets WHERE id = %s AND updated_at = %s
        """, (ticket_data["id"], ticket_data["updated_at"]))
        
        if cur.fetchone():
            # Update other fields for same id and updated_at
            cur.execute("""
                UPDATE tickets 
                SET priority=%s, status=%s, created_at=%s, customer_tier=%s
                WHERE id=%s AND updated_at=%s
            """, (ticket_data["priority"], ticket_data["status"], 
                  ticket_data["created_at"], ticket_data["customer_tier"],
                  ticket_data["id"], ticket_data["updated_at"]))
            conn.commit()
            return {"status": "UPDATED"}

        # Insert new ticket if not found
        cur.execute("""
            INSERT INTO tickets (id, priority, status, created_at, updated_at, customer_tier)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (ticket_data["id"], ticket_data["priority"], ticket_data["status"], 
              ticket_data["created_at"], ticket_data["updated_at"], ticket_data["customer_tier"]))
        conn.commit()
        return {"status": "CREATED"}
        
    except Exception as e:
        print("DB ERROR:", str(e))
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()
        conn.close()

def get_all_tickets(open=None):
    conn = get_db()
    cur = conn.cursor()
    if open:
        cur.execute("""
            SELECT * FROM tickets WHERE status = 'open'
        """)
    else:
        cur.execute("""
            SELECT * FROM tickets
        """)
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
    return tickets_json


