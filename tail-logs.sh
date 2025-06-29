#!/bin/bash

echo "=========================================="
echo "SLA Monitoring Service - Centralized Logs"
echo "=========================================="
echo "Press Ctrl+C to stop"
echo ""

# Tail all container logs with timestamps
docker-compose logs -f --timestamps 