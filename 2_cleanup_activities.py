import json
import os

def cleanup_activity(a):

    keep_keys = ["name", "distance", "elapsed_time", "total_elevation_gain", "id", "start_date_local"]

    d = {}

    for k in keep_keys:
        if k in a:
            d[k] = a[k]
        else:
            name = a["name"]
            print(f"-- missing key: {k}: {name}")

    if "map" in a and "summary_polyline" in a["map"]:
        d["polyline"] = a["map"]["summary_polyline"]

    return d    

clean_activities = []

for i in range(1, 10):
    print(i)

    p = f"raw_activities/activities_page_{i}.json"

    if not os.path.exists(p):
        break

    with open(p, 'r') as f:
    
        activities = json.load(f)

        ca = [cleanup_activity(a) for a in activities]

        clean_activities.extend(ca)

with open("activities_clean.json", 'w', encoding='utf-8') as f:
    count = len(clean_activities)
    print("**", count)
    print(f"-- writing {count} clean activities")
    json.dump(clean_activities, f, ensure_ascii=False, indent=4)

    
