import time
import sys
from DB.database import get_all_tickets
from SLACK.load_sla_yml import config_manager
from datetime import datetime, timezone
from SLACK.slack import slack_message_sender
from DB.database import create_sla_breach_alert_db, update_sla_breach_alert_db

class SLABreacher:
    def __init__(self):
        self.open_tickets = get_all_tickets(open=True)

    def sla_breacher(self):
   
        print('Checking for SLA Breach for open tickets, Total tickets: ', len(self.open_tickets))
        print('--------------------------------')
        sys.stdout.flush()

        for id, ticket in self.open_tickets.items():
            priority = ticket['priority'].lower()
            tier = ticket['customer_tier'].upper()
            sla_time = config_manager.config.get("sla_definitions", {}).get(tier, {}).get(priority)
            print(f"SLA Time: {sla_time} seconds for ticket: {id}")
            
            if not sla_time:
                print('SLA Breach Definition Not matched for ticket: ', id)
                sys.stdout.flush()
                continue
            
            ticket_created_at = ticket['created_at']
            ticket_created_at_datetime = datetime.fromisoformat(ticket_created_at.replace('Z', '+00:00'))
            current_time = datetime.now(timezone.utc)
            elapsed_time_seconds = (current_time - ticket_created_at_datetime).total_seconds()
            print(f"Elapsed time: {elapsed_time_seconds} seconds for ticket: {id}")
            
            elapsed_time_percentage = elapsed_time_seconds/sla_time * 100

            if elapsed_time_seconds/sla_time > 0.99:
                print('SLA Critical Breached for ticket: ', id)
                db_result = update_sla_breach_alert_db(ticket, elapsed_time_seconds, elapsed_time_percentage, "BREACH")
                if db_result.get("status") in ["CREATED", "UPDATED"]:
                    slack_message_sender(ticket, elapsed_time_seconds)
                sys.stdout.flush()
            elif elapsed_time_percentage > 85:
                print('SLA To be Breached for ticket: ', id)
                db_result = create_sla_breach_alert_db(ticket, elapsed_time_seconds, elapsed_time_percentage, "ALERT")
                if db_result.get("status") == "CREATED":
                    slack_message_sender(ticket, elapsed_time_seconds)
                sys.stdout.flush()
            else:
                print('SLA Not Breached for ticket: ', id, 'remaining time: ', sla_time - elapsed_time_seconds , 'seconds')
                sys.stdout.flush()

def main():
    print("Scheduler is running")
    sys.stdout.flush()
    while True:
        try:
            sla_breacher = SLABreacher()
            sla_breacher.sla_breacher()
            print(f"Scheduler completed check at {datetime.now()}")
            sys.stdout.flush()
            time.sleep(60)
        except Exception as e:
            print(f"Scheduler error: {e}")
            sys.stdout.flush()
            time.sleep(60)

if __name__ == "__main__":
    main()