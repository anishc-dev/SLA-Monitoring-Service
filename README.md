# SLA Monitoring Service
Demo: 
A comprehensive SLA (Service Level Agreement) monitoring system built with FastAPI, PostgreSQL, and Slack integration. The system automatically monitors ticket SLAs, detects breaches, and sends alerts via Slack.
![image](https://github.com/user-attachments/assets/54b85c75-cc0f-4984-92a7-faa00dfa9a3f)


## Architecture
Included as a .pdf document - Document for SLA Breach Engine.pdf
## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Git

### 1. Clone and Setup

```bash
git clone <repository-url>
cd SLA-Monitoring-Service
```

### 2. Start the Services

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps
```

### 3. Verify Services

```bash
# Check if all containers are running
docker-compose logs --tail=10

# Test the main API
curl http://localhost:8000/

# Test Slack mock service
curl http://localhost:5000/
```

## Usage Guide

### Creating Tickets

#### Single Ticket Creation

```bash
curl -X POST http://localhost:8000/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "id": 1001,
    "priority": "high",
    "status": "open",
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-01-15T10:00:00Z",
    "customer_tier": "P0"
  }'
```

#### Batch Ticket Creation

Create a script to generate multiple tickets:

```bash
#!/bin/bash

# Create batch tickets with different priorities and tiers
for i in {1..10}; do
  curl -X POST http://localhost:8000/tickets \
    -H "Content-Type: application/json" \
    -d "{
      \"id\": $((1000 + $i)),
      \"priority\": \"high\",
      \"status\": \"open\",
      \"created_at\": \"$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ)\",
      \"updated_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
      \"customer_tier\": \"P0\"
    }"
  echo "Created ticket $((1000 + $i))"
done
```

Save as `create_batch_tickets.sh` and run:
```bash
chmod +x create_batch_tickets.sh
./create_batch_tickets.sh
```

### Monitoring SLA Breaches

#### 1. View Dashboard

Open your browser and navigate to:
```
http://localhost:8000/dashboard
```

The dashboard shows:
- All tickets with their SLA status
- Relative time columns for created/updated timestamps
- Pagination (10 tickets per page)
- Filtering options (All, Breach Only, Alert Only)
- Real-time WebSocket alerts for SLA breaches

#### 2. View Alerts Only

```bash
curl http://localhost:8000/alerts
```

#### 3. Monitor Logs

```bash
# View all service logs
./tail-logs.sh

# View specific service logs
docker-compose logs -f scheduler
docker-compose logs -f sla-monitor
docker-compose logs -f slack-mock
```

### Configuration

#### SLA Definitions

Edit `SLACK/sla_config.yml` to modify SLA timeframes:

```yaml
scheduler_interval_seconds: 60  # Scheduler check interval

sla_definitions:
  P0:  # Premium tier
    high: 3600    # 1 hour
    medium: 7200  # 2 hours
    low: 14400    # 4 hours
  P1:  # Standard tier
    high: 7200    # 2 hours
    medium: 14400 # 4 hours
    low: 28800    # 8 hours
  # ... more tiers
```

#### Scheduler Interval

To change how frequently the scheduler checks for breaches:

```yaml
scheduler_interval_seconds: 30  # Check every 30 seconds
```

## API Endpoints

### Ticket Management

- `POST /tickets` - Create a new ticket
- `GET /tickets/{id}` - Get ticket by ID
- `GET /dashboard` - View SLA dashboard (HTML)
- `GET /alerts` - View SLA breach alerts (HTML)
- `WS /ws/alerts` - WebSocket endpoint for real-time alerts

### Health Checks

- `GET /` - API health check
- `GET /health` - Service health status

## Logging

The system uses structured JSON logging with:

- **Correlation IDs**: Track requests across services
- **Operation IDs**: Identify specific operations
- **Latency Tracking**: Monitor performance
- **Ticket IDs**: Link logs to specific tickets

### Log Examples

```json
{
  "timestamp": "2025-06-29T07:01:01.866661+00:00",
  "level": "error",
  "message": "SLA Critical Breached for ticket: 1003",
  "correlation_id": "6af39e2b-276b-49c2-9bf4-602d592c69d2",
  "ticket_id": "1003",
  "operation": "sla_critical_breach",
  "latency_ms": 0.03
}
```

## Development

### Project Structure

```
SLA-Monitoring-Service/
├── DB/                 # Database operations
├── ENGINE/             # Scheduler engine
├── ROUTES/             # FastAPI routes
├── SLACK/              # Slack integration
├── docker-compose.yml  # Docker configuration
├── requirements.txt    # Python dependencies
└── README.md          # This file
```
1. Check the logs: `./tail-logs.sh`
2. Review configuration: `SLACK/sla_config.yml`
3. Test endpoints: Use the provided curl commands
4. Check service status: `docker-compose ps`
