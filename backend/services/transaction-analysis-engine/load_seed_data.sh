#!/bin/bash

# Set database connection parameters
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=postgres
DB_PORT=5432
DB_NAME=aml_monitoring

# Path to the seed file
SEED_FILE="/app/seed_rules.sql"

# Check if the seed file exists
if [ ! -f "$SEED_FILE" ]; then
    echo "Error: Seed file not found at $SEED_FILE"
    exit 1
fi

# Load the seed data
echo "Loading seed data from $SEED_FILE..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f "$SEED_FILE"

# Check if the data was loaded successfully
if [ $? -eq 0 ]; then
    echo "Seed data loaded successfully!"
    
    # Verify the data was loaded
    echo "Verifying data..."
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT COUNT(*) as total_rules FROM regulatory_rules;"
else
    echo "Error loading seed data"
    exit 1
fi
