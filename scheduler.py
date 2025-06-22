import time
from database import get_db
def sla_breacher():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM tickets WHERE status = 'open'
    """)
    tickets = cur.fetchall()
    print(tickets)
    conn.close()        
        

def main():
    print("Scheduler is running")
    while True:
        sla_breacher()
        time.sleep(60)

if __name__ == "__main__":
    main()