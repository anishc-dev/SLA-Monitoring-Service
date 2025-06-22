import psycopg2
import os

def get_db():
    return psycopg2.connect(os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/sla_monitor"))

def create_table_if_not_exists(table_name, columns, primary_key):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns}, PRIMARY KEY ({primary_key}))")
    conn.commit()
    cur.close()
    conn.close()

def init_db():
    create_table_if_not_exists(
        "tickets", "id INTEGER, priority VARCHAR(10), status VARCHAR(20), created_at VARCHAR(50), updated_at VARCHAR(50), \
         customer_tier VARCHAR(10), escalation_level VARCHAR(10), elapsed_time_percentage INTEGER, elapsed_time_seconds INTEGER", "id")
    create_table_if_not_exists("sla_breach_alerts", "id SERIAL, ticket_id INTEGER, priority VARCHAR(10), status VARCHAR(20), \
        created_at VARCHAR(50), updated_at VARCHAR(50), customer_tier VARCHAR(10), elapsed_time_seconds INTEGER, elapsed_time_percentage INTEGER, \
        escalation_level VARCHAR(10)", "id")

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

def get_ticket_by_id(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM tickets WHERE id = %s
    """, (id,))
    ticket = cur.fetchone()
    cur.close() 
    conn.close()
    return ticket

def get_dashboard_data():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM tickets
    """)
    dashboard_data = cur.fetchall()
    cur.close()
    conn.close()
    return dashboard_data

def create_sla_breach_alert_db(ticket_data, elapsed_time_seconds, elapsed_time_percentage, escalation_level):
    conn = get_db()
    cur = conn.cursor()
    
    try:
        # Check if an alert already exists for this ticket and escalation level
        cur.execute("""
            SELECT id FROM sla_breach_alerts 
            WHERE ticket_id = %s AND escalation_level = %s
        """, (ticket_data["id"], escalation_level))
        
        if cur.fetchone():
            # Record already exists, don't create duplicate
            print(f"Alert already exists for ticket {ticket_data['id']} with escalation level {escalation_level}")
            return {"status": "EXISTS"}
        
        # Create new alert record
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

        return {"status": "CREATED"}
        
    except Exception as e:
        print("DB ERROR:", str(e))
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()
        conn.close()

def update_sla_breach_alert_db(ticket_data, elapsed_time_seconds, elapsed_time_percentage, escalation_level):
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
            return {"status": "UPDATED"}
        else:
            # Create new record if none exists
            print(f"Alert does not exist for ticket {ticket_data['id']} with escalation level {escalation_level}")
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
            return {"status": "CREATED"}
            
    except Exception as e:
        print("DB ERROR:", str(e))
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()
        conn.close()



