# https://pdf-to-book.bookfactory.ch/fr

import requests
import urllib3
import os
import logging
import polyline_decoder
import json
import json_utils
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch_geo(activity_ids):
    
    print("**-- activity_ids:", activity_ids)
    
    aids_str = [str(aid) for aid in activity_ids]
    joined_aids = str('_'.join(aids_str))
    
    lat, lon = None, None
    
    for aid in activity_ids:
        activity_file = f"pages/{joined_aids}/{aid}.json"

        if os.path.exists(activity_file):
            a = json_utils.load(activity_file)

            if "polyline" in a:
                p = a["polyline"]
                
                if not p:
                    continue

                [(lat, lon)] = polyline_decoder.decode_polyline_lat_lon(p, only_first=True)
                break
    
    if not lat or not lon:
        return None
    
    #print(lat, lon)
        
    # https://api.maptiler.com/maps/a21bea99-ab0d-49c3-9900-8640bbe2e9c7/static/auto/600x600@2x.png?path=stroke:red|fill:none|enc:_p~iF~ps|U_ulLnnqC_mqNvxq`@&key=xxx&markers=-120.2,38.5,green
    
    # https://cloud.maptiler.com/maps/editor?map=a21bea99-ab0d-49c3-9900-8640bbe2e9c7#14.86/46.3856/8.02434
    
    query_params = [
        ("key", config.MAPTILER_API_KEY),
        ("language", ["fr"])#,
        #("types", ["municipality", "place"])
    ]
    
    url = f"https://api.maptiler.com/geocoding/{lon},{lat}.json"

    print("**", url)
    print("-- query_params:", query_params)
    
    response = requests.get(
        url,
        params=query_params,
        verify=False)    
    
    if response.status_code != 200:
        print(response.status_code)
        print(response.text)
        return
        
    d = response.json()
            
    features = d["features"]

    place_name = None
    
    preferred_place_type_name = ['commune', 'lieu', 'pays']
    
    for f in features:
        if place_name:
            break
        
        if not f['type'] == "Feature":
            continue
        
        properties = f['properties']
        
        print("-> ?", properties["place_type_name"], f)
        
        for ptn in preferred_place_type_name:
            if ptn in properties["place_type_name"]:
                place_name = f["place_name_fr"]
                break
    
    print("--1", place_name)
    
    if not place_name:
        return None
    
    suffix_to_remove = ", Suisse"
    if place_name.endswith(suffix_to_remove):
        place_name = place_name[:-len(suffix_to_remove)]

    print("--2", place_name)
    
    return place_name
    
if __name__ == "__main__":
    
    fetch_geo(["6406797632"])
    fetch_geo(["7425508699"])
    fetch_geo(["7446484349"])
    fetch_geo(["7472671840"])
    fetch_geo(["9062353745"])
    
    
    

