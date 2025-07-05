import asyncio
import sys
from DB.database import get_all_tickets
from SLACK.load_sla_yml import config_manager
from datetime import datetime, timezone
from SLACK.slack import slack_message_sender
from DB.database import create_sla_breach_alert_db, update_sla_breach_alert_db
from logger import info, error, set_operation, set_ticket_id, set_correlation_id, start_timer
import uuid
import json

# Import the broadcast function from listener
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ROUTES.listener import broadcast_alert

class SLABreacher:
    def __init__(self):
        start_timer()
        self.open_tickets = get_all_tickets(open=True)
        info("SLA Breacher initialized", total_tickets=len(self.open_tickets))

    async def sla_breacher(self):
        set_operation("sla_breach_check")
        set_correlation_id(str(uuid.uuid4()))
   
        info("Checking for SLA Breach for open tickets", total_tickets=len(self.open_tickets))
        sys.stdout.flush()

        for id, ticket in self.open_tickets.items():
            start_timer()
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
                    # Broadcast WebSocket alert
                    try:
                        alert_data = {
                            "type": "BREACH",
                            "ticket_id": id,
                            "priority": priority,
                            "customer_tier": tier,
                            "elapsed_time": elapsed_time_seconds,
                            "elapsed_percentage": elapsed_time_percentage,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        await broadcast_alert(alert_data)
                        info(f"WebSocket alert broadcasted successfully for ticket {id}")
                    except Exception as e:
                        error(f"WebSocket broadcast error: {e}")
                sys.stdout.flush()
            elif elapsed_time_percentage > 85:
                set_operation("sla_warning_alert")
                error(f"SLA To be Breached for ticket: {id}")
                db_result = create_sla_breach_alert_db(ticket, elapsed_time_seconds, elapsed_time_percentage, "ALERT")
                if db_result.get("status") == "CREATED":
                    slack_message_sender(ticket, elapsed_time_seconds)
                    # Broadcast WebSocket alert
                    try:
                        alert_data = {
                            "type": "ALERT",
                            "ticket_id": id,
                            "priority": priority,
                            "customer_tier": tier,
                            "elapsed_time": elapsed_time_seconds,
                            "elapsed_percentage": elapsed_time_percentage,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        info(f"Broadcasting WebSocket alert for ticket {id}")
                        await broadcast_alert(alert_data)
                        info(f"WebSocket alert broadcasted successfully for ticket {id}")
                    except Exception as e:
                        error(f"WebSocket broadcast error: {e}")
                sys.stdout.flush()
            else:
                set_operation("sla_status_check")
                info(f"SLA Not Breached for ticket: {id}, remaining time: {sla_time - elapsed_time_seconds} seconds")
                sys.stdout.flush()

async def main():
    set_operation("scheduler_main_loop")
    info("Scheduler is running")
    sys.stdout.flush()
    while True:
        try:
            start_timer()
            sla_breacher = SLABreacher()
            await sla_breacher.sla_breacher()
            info(f"Scheduler completed check at {datetime.now()}")
            sys.stdout.flush()
            interval = config_manager.config.get('scheduler_interval_seconds', 60)
            await asyncio.sleep(interval)
        except Exception as e:
            set_operation("scheduler_error_handling")
            error(f"Scheduler error: {e}")
            sys.stdout.flush()
            interval = config_manager.config.get('scheduler_interval_seconds', 60)
            await asyncio.sleep(interval)

if __name__ == "__main__":
    asyncio.run(main())