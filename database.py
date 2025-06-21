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
        cur.execute("""
            INSERT INTO tickets (id, priority, status, created_at, updated_at, customer_tier)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                priority = EXCLUDED.priority,
                status = EXCLUDED.status,
                updated_at = EXCLUDED.updated_at,
                customer_tier = EXCLUDED.customer_tier
        """, (ticket_data["id"], ticket_data["priority"], ticket_data["status"], 
              ticket_data["created_at"], ticket_data["updated_at"], ticket_data["customer_tier"]))
        conn.commit()
        return {"status": "success"}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()
        conn.close()

