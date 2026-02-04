#!/bin/bash

# Start Postgres
docker run -d \
  --name test-postgres \
  -e POSTGRES_PASSWORD=Kis123!! \
  -e POSTGRES_DB=markets \
  -p 5432:5432 \
  postgres:15

echo "Waiting for Postgres to start..."
sleep 5

# Set env vars and run script
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=markets
export POSTGRES_PASSWORD=Kis123!!

python3.11 polymarket_api.py

# Check results (remove -it flag for scripts)
echo "Checking inserted data..."
docker exec test-postgres psql -U postgres -d markets -c "SELECT COUNT(*) FROM current_markets;"

# Cleanup
#echo "Cleanup: docker stop test-postgres && docker rm test-postgres"
#docker stop test-postgres && docker rm test-postgres