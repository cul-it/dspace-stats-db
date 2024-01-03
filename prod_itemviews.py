import psycopg2
import json
import requests
import os
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

#Directory for txt files and base url for your DSpace api.
directory = os.getenv("SERVER_DIR")
base_url = os.getenv("API_URL")

# Checkpoint file to store the last processed item_id
checkpoint_file = os.path.join(directory, "checkpoint.txt")

# File to store the UUIDs
uuid_file = os.path.join(directory, "uuids.txt")

# Function to get the last checkpointed item_id
def get_last_checkpoint():
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, "r") as f:
            last_checkpoint = f.read().strip()
            return last_checkpoint
    return None

# Function to update the checkpoint with the last processed UUID
def update_checkpoint(uuid):
    with open(checkpoint_file, "w") as f:
        if uuid is not None:
            f.write(uuid)


# Function to write UUIDs to a file
def write_uuids_to_file(uuids):
    with open(uuid_file, "w") as f:
        for uuid in uuids:
            f.write(uuid + "\n")

# Function to read UUIDs from a file starting from the last checkpointed UUID
def read_uuids_from_checkpoint(chunk_size):
    last_checkpoint = get_last_checkpoint()
    with open(uuid_file, "r") as f:
        uuids = [line.strip() for line in f]
        if last_checkpoint and last_checkpoint in uuids:
            start_index = uuids.index(last_checkpoint)
            uuids = uuids[start_index:]
        for i in range(0, len(uuids), chunk_size):
            yield uuids[i:i + chunk_size]

# Function to check if the `uuids.txt` file was last modified more than x amount of seconds
def is_file_older_than_x(file_path):
    if os.path.exists(file_path):
        file_modified_time = os.path.getmtime(file_path)
        current_time = time.time()
        time_difference = current_time - file_modified_time
        return time_difference > 7 * 24 * 60 * 60  # One week in seconds
    return True  # File doesn't exist, treat it as older than x


# Get the last checkpointed item_id
last_checkpoint = get_last_checkpoint()

# Use the environment variables in your script
source_db_params = {
    "host": os.getenv("SOURCE_DB_HOST"),
    "database": os.getenv("SOURCE_DB_DATABASE"),
    "user": os.getenv("SOURCE_DB_USER"),
    "password": os.getenv("SOURCE_DB_PASSWORD")
}

dest_db_params = {
    "host": os.getenv("DEST_DB_HOST"),
    "database": os.getenv("DEST_DB_DATABASE"),
    "user": os.getenv("DEST_DB_USER"),
    "password": os.getenv("DEST_DB_PASSWORD")
}
# Check if `uuids.txt` is older than 24 hours
if is_file_older_than_x(uuid_file):
    source_conn = psycopg2.connect(**source_db_params)
    source_cursor = source_conn.cursor()

    # Query to retrieve all item_id values from the source database
    query = "SELECT uuid FROM item WHERE withdrawn IS FALSE AND in_archive IS TRUE AND discoverable IS TRUE ORDER BY uuid"
    source_cursor.execute(query)

    # Extract the item_id values from the result list
    item_id_results = source_cursor.fetchall()
    item_ids = [result[0] for result in item_id_results]

    # Close the cursor and connection for the source database
    source_cursor.close()
    source_conn.close()

    # Write UUIDs to a file
    write_uuids_to_file(item_ids)
else:
    print("uuids.txt not old enough, skipping query")

# Create a connection to the destination database
dest_conn = psycopg2.connect(**dest_db_params)
dest_cursor = dest_conn.cursor()

# Create a table for the JSON data with separate columns for points data
#dest_cursor.execute("DROP TABLE api_itemview_stats")
dest_cursor.execute("""
    CREATE TABLE IF NOT EXISTS api_itemview_stats (
        id VARCHAR(255) PRIMARY KEY,
        item_id uuid,
        title VARCHAR,
        views INTEGER,
        type VARCHAR(255),
        type_usage VARCHAR(255),
        _links JSONB
    )
""")

# Read UUIDs from the file in chunks
chunk_size = 200
# Loop through each item_id and fetch data from the API
for item_id_chunk in read_uuids_from_checkpoint(chunk_size):
    for item_id in item_id_chunk:
        # Make an API request to fetch JSON data for the item_id
        api_url = f"{base_url}/server/api/statistics/usagereports/{item_id}_TotalVisits"
        response = requests.get(api_url)

        if response.status_code == 200:
            data = response.json()
            # Remove "_TotalVistits" from the "id" field
            data["id"] = data["id"].replace("_TotalVisits", "")

            # Insert the JSON data into the PostgreSQL table
            for point in data["points"]:
                dest_cursor.execute("""
                    INSERT INTO api_itemview_stats (id, item_id, title, views, type, type_usage, _links)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE
                    SET views = CASE WHEN api_itemview_stats.views > EXCLUDED.views
                                    THEN api_itemview_stats.views
                                    ELSE EXCLUDED.views
                            END;
                """, (
                    data["id"],
                    point["id"],
                    point["label"],
                    point["values"]["views"],
                    point["type"],
                    data["type"],
                    json.dumps(data["_links"])
                ))

            print(f"Data for item_id {item_id} inserted or updated.")
            #Commit for each item_id
            dest_conn.commit()
        else:
            print(f"Failed to retrieve data for item_id {item_id} from the API.")
        # Update the checkpoint to the current item_id
        update_checkpoint(item_id)
    # Check if the end of the file is reached
    if len(item_id_chunk) < chunk_size:
        # Reset the checkpoint to start from the beginning
        update_checkpoint(None)
    #echo
    print (chunk_size, "items inserted or updated at", datetime.now(), ".")
    #finish
    break

dest_cursor.close()
dest_conn.close()
