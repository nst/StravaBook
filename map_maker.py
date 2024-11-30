import requests
import urllib3
import os
import sys
import polyline_decoder
import json_utils
import config

import page_creator

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# TODO: limit aids to 4

def map_file_path(activity_ids):
    aids_str = [str(aid) for aid in activity_ids]
    joined_aids = str('_'.join(aids_str))
    return f"pages/{joined_aids}/{joined_aids}_map.png"

def get_map(activity_ids):    
    filename = map_file_path(activity_ids)
    
    if not os.path.exists(filename):
        fetch_map(activity_ids)
    
    return filename

def fetch_map(activity_ids):
    
    if len(config.MAPTILER_API_KEY) == 0:
        print("(!) MAPTILER_API_KEY is missing")
        sys.exit(1)
    
    print(f"-- fetch_map for {activity_ids}:")
    
    aids_str = [str(aid) for aid in activity_ids]
    joined_aids = str('_'.join(aids_str))

    polylines_for_map = []
    markers_for_map = []
    
    lat, lon = None, None
    
    for aid in activity_ids:
        activity_file = f"pages/{joined_aids}/{aid}.json"

        if not os.path.exists(activity_file):
            print("** no file", activity_file)
        else:
            a = json_utils.load(activity_file)
            if "polyline" in a:
                p = a["polyline"]
                
                if not p:
                    continue

                polylines_for_map.append(p)
                
                [(lat, lon)] = polyline_decoder.decode_polyline_lat_lon(p, only_first=True)
                markers_for_map.append((lat, lon))
    
    if not lat or not lon:
        print(f"-- no lat or lon for {aid}")
        return
    
    activity_file = f"pages/{joined_aids}/{joined_aids}_processed.json"
    if os.path.exists(activity_file):
        a = json_utils.load(activity_file)
    
    # https://api.maptiler.com/maps/a21bea99-ab0d-49c3-9900-8640bbe2e9c7/static/auto/600x600@2x.png?path=stroke:red|fill:none|enc:_p~iF~ps|U_ulLnnqC_mqNvxq`@&key=xxx&markers=-120.2,38.5,green
    
    # https://cloud.maptiler.com/maps/editor?map=a21bea99-ab0d-49c3-9900-8640bbe2e9c7#14.86/46.3856/8.02434
    
    query_params = [
        ("key", config.MAPTILER_API_KEY),
        ("attribution", "false")#,
        #("padding", "0.05")
    ]
    
    for p in polylines_for_map:
        query_params.append(("path", f"stroke:red|fill:none|width:2|enc:{p}"))
    
    for lat,lon in markers_for_map:
        query_params.append(("markers", f"{lon},{lat},green"))
    
    custom_map_id = "a21bea99-ab0d-49c3-9900-8640bbe2e9c7"
    
    factor = 1.74 # increase for more details / resolution

    from reportlab.lib.units import mm, cm
    w, h = int((205*mm + 2*mm) * factor), int((182 + 1*mm) *factor) # including cut margins
    
    url = f"https://api.maptiler.com/maps/{custom_map_id}/static/auto/{w}x{h}@2x.png"
        
    print("**", url)
    #print("-- query_params:", query_params)
    
    response = requests.get(
        url,
        params=query_params,
        verify=False)
    
    if response.status_code != 200:
        print(response.status_code)
        print(response.text)
        return
    
    filename = map_file_path(activity_ids)
    
    try:
        with open(filename, "wb") as f:
            f.write(response.content)
            print(f"-- wrote {filename}")
    except Exception as e:
        print(e)