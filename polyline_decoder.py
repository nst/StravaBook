def decode_polyline_lat_lon(p, only_first=False): # [(float, float), (float, float), ...]

    # adapted from https://github.com/frederickjansen/polyline/blob/master/src/polyline/polyline.py

    def _trans(value, index):
        byte, result, shift = None, 0, 0
    
        comp = None
        while byte is None or byte >= 0x20:
            byte = ord(value[index]) - 63
            index += 1
            result |= (byte & 0x1f) << shift
            shift += 5
            comp = result & 1
    
        return ~(result >> 1) if comp else (result >> 1), index

    coordinates, index, lat, lng, length = [], 0, 0, 0, len(p)

    while index < length:
        lat_change, index = _trans(p, index)
        lng_change, index = _trans(p, index)
        lat += lat_change
        lng += lng_change
        
        lat_lon_tuple = (lat / 10 ** 5, lng / 10 ** 5)
        
        if only_first:
            return [lat_lon_tuple]
        
        coordinates.append(lat_lon_tuple)

    return coordinates
