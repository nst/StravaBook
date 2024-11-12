import requests
import urllib3
import json
import os
import config
import sys

import polyline_decoder

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#def delete_old_file(strava_id):
#
#    filename = f"pages/{strava_id}/{strava_id}_elevation.json"
#    
#    if os.path.exists(filename):
#        print(f"-- removing {filename}")
#        os.remove(filename)

def get_elevations(polyline, joined_ids, strava_id):
    #print("-- get_elevations", strava_id)
    
    elevations = read_elevations(joined_ids, strava_id)
    if elevations:
        return elevations
    
    elevations = fetch_elevations(polyline)
    
    if not elevations:
        print(f"-- no elevations for strava_id {strava_id}")
        return None
    
    #all_zero_elevations = sum(elevations) < 1    
    #if all_zero_elevations:
    #    return None
    
    save_elevations(elevations, joined_ids, strava_id)
    
    return elevations
    
def read_elevations(joined_ids, strava_id):
    #print("-- read_elevations")

    filename = f"pages/{joined_ids}/{strava_id}_elevations.json"

    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    
    return None

def save_elevations(elevations, joined_ids, strava_id):
    print("-- save_elevations")

    filename = f"pages/{joined_ids}/{strava_id}_elevations.json"
    
    try:
        with open(filename, 'w') as f:
            json.dump(elevations, f, indent=4)
            print(f"-- wrote: {filename}")
    except Exception as e:
        print(e)

def fetch_elevations(encoded_polyline):

    # see also https://api.open-elevation.com/api/v1/lookup?locations=41.161758,-8.583933

    if len(config.STADIA_API_KEY) == 0:
        print("(!) STADIA_API_KEY is missing")
        sys.exit(1)
    

    # https://docs.stadiamaps.com/elevation/
    
    query_params = {
        "encoded_polyline":encoded_polyline,
        "api_key":config.STADIA_API_KEY,
        "shape_format":"polyline5"
    }
    
    url = "https://api.stadiamaps.com/elevation/v1"

    response = requests.post(
        url,
        params=query_params,
        verify=False)    
    
    if response.status_code != 200:
        print(response.status_code)
        print(response.text)
        return
    
    d = response.json()
    return d["height"]

if __name__ == "__main__":
    
    p = "ivuxG}~nm@ARFFAIGHCPi@`AOLc@PSFg@?WLKRETQLMBu@u@Se@_@k@_@US?YNKX@J@DXZDlAC`@EBCCF?E?@HGf@Ib@@p@L\\\\JDV@G[t@e@v@Qr@AHBFf@GnBOJDPLz@\\DDA@DDn@D`@PPA@BCNBHb@ON?@Pk@nACLBDvAm@|@gAHQ@MCe@F]`Ag@b@[JCPMV?JEHMZJVEVFR@LGA?BB@EXGVUEn@MXE`@EH@Bh@M`Ae@XIL@IDBZE\\CDCP?XId@HKbA_@XSXCx@c@XKb@GLNG\\o@j@Al@IJ?DDC?E~Ai@Xo@b@_@d@ERBFGj@?NCLMTGJFJRPJD@NIJDLWHId@Bv@YXE@FS`@CRPGQ@J@AMC@FFCCD@G?B?Mf@]^WB@CBFREhA?JGNC`@N^CJDBHFBHWHNVDb@VNB?@EBB@D@BEADHJBC?F@IABHAFECCAHLDBOGJ?FH`@\\HFHDTAHDJPV?`@FRGTBZN@h@PRMAMDONEX?p@KLB^VF?ZM^BPFFCNSRMACp@?BDSNIRAJLj@PHhALl@\\?HCFOLYd@ZZj@ZP`@LJJDCFm@GUP@FAGm@HK@WIe@LOEk@V]nA[XM^k@\\i@DQIIHCLAEAFVRDN@AABAC@F?GG@BCAFDK?DMFFKIJDEADB?E@DEB@GBNOKL[HIA_@Vy@La@Le@l@]RSXk@NQRg@PUVOCVZ?B?EDCFBDJNF@FSJK\\WXkAY_@r@[f@Sj@a@`@yApBUPB@AEDCE@ABB@C@AFIBQPGXMV@PBLPVHHBCCA@AJLe@`@g@XUX_@Lm@b@kAbAe@v@[^CD?PCCR`@f@@ZFd@h@NZHHf@N\\\\R?T`@F\\S@[NKHC?BCC@?BPNDT\\v@\\`@JZTtADDBAF`@PZn@r@p@\\\\^JRJp@@Z?XFn@RrAJHXB\\EEGJBTt@V\\DR@d@DRBJJJTBBCADBE^h@XHPK@IACA@FFE?FJH@p@q@D@L\\CG`@j@@JM`@@NCRL\\CR@ZHZB?G?FF?NCNCAPRDPEf@IBFFEBGA@F?EEADVEZAC@ABDCJ?GAA@?KVBHEBIf@A?CH?HE@ARQb@B??DGZIPBFMLANc@ZEFi@_@E@Q^_@d@CA"
    
    elevations = fetch_elevations(p)
    
    print(elevations)
