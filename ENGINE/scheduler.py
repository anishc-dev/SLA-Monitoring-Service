import time
import sys
from DB.database import get_all_tickets
from SLACK.load_sla_yml import config_manager
from datetime import datetime, timezone
from SLACK.slack import slack_message_sender
from DB.database import create_sla_breach_alert_db, update_sla_breach_alert_db
from logger import info, error, set_operation, set_ticket_id, set_correlation_id
import uuid

class SLABreacher:
    def __init__(self):
        self.open_tickets = get_all_tickets(open=True)

    def sla_breacher(self):
        set_operation("sla_breach_check")
        set_correlation_id(str(uuid.uuid4()))
   
        info("Checking for SLA Breach for open tickets", total_tickets=len(self.open_tickets))
        info("SLA breach check started", separator="--------------------------------")
        sys.stdout.flush()

        for id, ticket in self.open_tickets.items():
            set_ticket_id(str(id))
            set_operation("sla_breach_analysis")
            priority = ticket['priority'].lower()
            tier = ticket['customer_tier'].upper()
            sla_time = config_manager.config.get("sla_definitions", {}).get(tier, {}).get(priority)
            info(f"SLA Time: {sla_time} seconds for ticket: {id}")
            
            if not sla_time:
                error(f"SLA Breach Definition Not matched for ticket: {id}")
                sys.stdout.flush()
                continue
            
            ticket_created_at = ticket['created_at']
            ticket_created_at_datetime = datetime.fromisoformat(ticket_created_at.replace('Z', '+00:00'))
            current_time = datetime.now(timezone.utc)
            elapsed_time_seconds = (current_time - ticket_created_at_datetime).total_seconds()
            info(f"Elapsed time: {elapsed_time_seconds} seconds for ticket: {id}")
            
            elapsed_time_percentage = elapsed_time_seconds/sla_time * 100

            if elapsed_time_seconds/sla_time > 0.99:
                set_operation("sla_critical_breach")
                error(f"SLA Critical Breached for ticket: {id}")
                db_result = update_sla_breach_alert_db(ticket, elapsed_time_seconds, elapsed_time_percentage, "BREACH")
                if db_result.get("status") in ["CREATED", "UPDATED"]:
                    slack_message_sender(ticket, elapsed_time_seconds)
                sys.stdout.flush()
            elif elapsed_time_percentage > 85:
                set_operation("sla_warning_alert")
                error(f"SLA To be Breached for ticket: {id}")
                db_result = create_sla_breach_alert_db(ticket, elapsed_time_seconds, elapsed_time_percentage, "ALERT")
                if db_result.get("status") == "CREATED":
                    slack_message_sender(ticket, elapsed_time_seconds)
                sys.stdout.flush()
            else:
                set_operation("sla_status_check")
                info(f"SLA Not Breached for ticket: {id}, remaining time: {sla_time - elapsed_time_seconds} seconds")
                sys.stdout.flush()

def main():
    set_operation("scheduler_main_loop")
    info("Scheduler is running")
    sys.stdout.flush()
    while True:
        try:
            sla_breacher = SLABreacher()
            sla_breacher.sla_breacher()
            info(f"Scheduler completed check at {datetime.now()}")
            sys.stdout.flush()
            time.sleep(60)
        except Exception as e:
            error(f"Scheduler error: {e}")
            sys.stdout.flush()
            time.sleep(60)

if __name__ == "__main__":
    main()