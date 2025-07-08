import csv
import json
import os
from urllib.parse import urlparse

def normalize_url(url):
    """Normalize URL for fuzzy matching: remove protocol, trailing slash, and query params."""
    if not url:
        return ""
    parsed = urlparse(url)
    return parsed.netloc + parsed.path.rstrip('/')

def make_schedule_filename(row, mdb_source_id):
    country = row['Country'].lower()
    region = row['Region (e.g Province, State)'].lower().replace(' ', '-')
    municipality = row['Municipality'].lower().replace(' ', '-') if row['Municipality'] else ''
    provider = row['Transit Provider'].lower().replace(' ', '-').replace('.', '')
    parts = [country, region]
    if municipality:
        parts.append(municipality)
    parts.append(provider)
    return f"{'-'.join(parts)}-gtfs-{mdb_source_id}"

def make_realtime_filename(row, mdb_source_id):
    country = row['Country'].lower() if row['Country'] else 'unknown'
    region = row['Region (e.g Province, State)'].lower().replace(' ', '-') if row['Region (e.g Province, State)'] else 'unknown'
    provider = row['Transit Provider'].lower().replace(' ', '-').replace('.', '')
    entity_map = {
        "Trip Updates": "tu",
        "Vehicle Positions": "vp",
        "Service Alerts": "sa"
    }
    entity = entity_map.get(row['Data type'].split(' - ')[-1], 'rt')
    return f"{country}-{region}-{provider}-gtfs-rt-{entity}-{mdb_source_id}"

def create_schedule_json(row, mdb_source_id, out_folder):
    filename = make_schedule_filename(row, mdb_source_id)
    feed = {
        "mdb_source_id": mdb_source_id,
        "data_type": "gtfs",
        "provider": row["Transit Provider"],
        "location": {
            "country_code": row["Country"],
            "subdivision_name": row["Region (e.g Province, State)"],
            "municipality": row["Municipality"],
            "bounding_box": {
                "minimum_latitude": None,
                "maximum_latitude": None,
                "minimum_longitude": None,
                "maximum_longitude": None,
                "extracted_on": "2025-07-08T00:00:00+00:00"
            }
        },
        "urls": {
            "direct_download": row["Download URL"],
            "license": row["License URL"],
            "latest": f"https://storage.googleapis.com/storage/v1/b/mdb-latest/o/{filename}.zip?alt=media"
        },
        "is_official": "True"
    }
    if row.get("User interview email"):
        feed["feed_contact_email"] = row["User interview email"]
    with open(os.path.join(out_folder, f"{filename}.json"), "w") as f:
        json.dump(feed, f, indent=4)
    return filename

def create_realtime_json(row, mdb_source_id, schedule_mapping, out_folder):
    filename = make_realtime_filename(row, mdb_source_id)
    static_ref = []
    if row.get("Link to associated GTFS Schedule feed "):
        norm = normalize_url(row["Link to associated GTFS Schedule feed "])
        if norm in schedule_mapping:
            static_ref = [schedule_mapping[norm]]
    entity_map = {
        "Trip Updates": "tu",
        "Vehicle Positions": "vp",
        "Service Alerts": "sa"
    }
    entity = entity_map.get(row['Data type'].split(' - ')[-1], 'rt')
    feed = {
        "mdb_source_id": mdb_source_id,
        "data_type": "gtfs-rt",
        "entity_type": [entity],
        "provider": row["Transit Provider"],
        "urls": {
            "direct_download": row["Download URL"]
        },
        "is_official": "True",
        "static_reference": static_ref
    }
    if row.get("User interview email"):
        feed["feed_contact_email"] = row["User interview email"]
    if row.get("License URL"):
        feed["license"] = row["License URL"]
    if "Authentication Type" in row and row["Authentication Type"] and row["Authentication Type"] != "None - 0":
        feed["urls"]["authentication_type"] = int(row["Authentication Type"].split(" - ")[-1])
        if row.get("API Key URL"):
            feed["urls"]["authentication_info"] = row["API Key URL"]
        if row.get("HTTP header or API key parameter name"):
            feed["urls"]["api_key_parameter_name"] = row["HTTP header or API key parameter name"]
    with open(os.path.join(out_folder, f"{filename}.json"), "w") as f:
        json.dump(feed, f, indent=4)
    return filename

# Main process
input_csv = "OpenMobilityData source updates - PROD - GTFS Catalog.csv"
schedule_json_folder = "catalogs/sources/gtfs/schedule"
realtime_json_folder = "catalogs/sources/gtfs/realtime"

# 1. First pass: create schedule feeds and build mapping
schedule_mapping = {}
next_schedule_id = 3000
next_realtime_id = 4000
rows = []
with open(input_csv, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        rows.append(row)
        if row.get('Data type', '').strip() == 'GTFS Schedule':
            filename = create_schedule_json(row, next_schedule_id, schedule_json_folder)
            schedule_mapping[normalize_url(row["Download URL"])] = str(next_schedule_id)
            row['__assigned_id'] = next_schedule_id
            next_schedule_id += 1

# 2. Second pass: create realtime feeds, using mapping for static_reference
for row in rows:
    if 'Realtime' in row.get('Data type', ''):
        create_realtime_json(row, next_realtime_id, schedule_mapping, realtime_json_folder)
        next_realtime_id += 1

print("All feeds created and linked with fuzzy matching!")
