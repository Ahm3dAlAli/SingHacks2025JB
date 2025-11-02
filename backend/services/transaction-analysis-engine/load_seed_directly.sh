#!/bin/bash

# Set database connection parameters
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=aml_postgres
DB_PORT=5432
DB_NAME=aml_monitoring

# Path to the seed file (inside the container)
SEED_FILE="/tmp/seed_rules.sql"

# Copy the seed file to the container
echo "Copying seed file to PostgreSQL container..."
docker cp ./backend/services/transaction-analysis-engine/database/seed_rules.sql ${DB_HOST}:/tmp/

# Execute the seed file in the PostgreSQL container
echo "Executing seed file in PostgreSQL container..."
docker exec -i ${DB_HOST} psql -U ${DB_USER} -d ${DB_NAME} -f ${SEED_FILE}

# Verify the data was loaded
echo "Verifying data was loaded..."
docker exec -i ${DB_HOST} psql -U ${DB_USER} -d ${DB_NAME} -c "SELECT COUNT(*) as total_rules FROM regulatory_rules;"

echo "Seed data loading process completed."
