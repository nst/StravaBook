import numpy as np
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Line, PolyLine, String, Polygon
from reportlab.graphics import renderPDF

def select_tick_interval(total_distance_km):
    """
    Select the best tick interval based on the total distance.
    The interval should be a multiple of 1, 2, 5, or 10 km and should ensure around 2-3 ticks on the x-axis.
    """
    if total_distance_km <= 5:
        return 1  # Use 1 km intervals for very short distances
    elif total_distance_km <= 10:
        return 2  # Use 2 km intervals for distances between 3 and 6 km
    elif total_distance_km <= 20:
        return 5  # Use 5 km intervals for distances between 6 and 15 km
    else:
        return 10  # Use 10 km intervals for distances above 15 km

def select_y_ticks(min_altitude, max_altitude):
    """
    Select y-axis ticks (elevation) using larger intervals and ensure no more than 5 ticks.
    """
    range_altitude = max_altitude - min_altitude
    
    # Choose intervals based on the altitude range
    if range_altitude > 4000:
        tick_interval = 1000
    elif range_altitude > 1000:
        tick_interval = 500
    elif range_altitude > 400:
        tick_interval = 200
    elif range_altitude > 200:
        tick_interval = 100
    elif range_altitude > 100:
        tick_interval = 50
    else:
        tick_interval = 20
    
    # Calculate the first and last tick to ensure they are within the range
    first_tick = np.ceil(min_altitude / tick_interval) * tick_interval
    last_tick = np.floor(max_altitude / tick_interval) * tick_interval
    
    # Generate the tick values
    ticks = np.arange(first_tick, last_tick + tick_interval, tick_interval)
    
    # Limit the number of ticks to 5
    if len(ticks) > 5:
        step = len(ticks) // 5
        ticks = ticks[::step]
    
    return ticks

def smooth_altitudes(altitudes, total_distance_meters, window_size = 2):
    
    smoothed_altitudes = [0] * len(altitudes)
    
    for i in range(len(altitudes)):
        window_start = max(0, i - window_size // 2)
        window_end = min(len(altitudes), i + window_size // 2 + 1)
        
        altitude_window = altitudes[window_start:window_end]
        
        smoothed_altitudes[i] = sum(altitude_window) / len(altitude_window)

    return smoothed_altitudes

def altitudes_from_elevations_lists(elevations_lists, distances_list, chart_width = 200):
        
    chart_width = int(chart_width)
    
    assert(len(elevations_lists) == len(distances_list))
        
    total_distance_in_meters = sum(distances_list)
    
    cumulated_distances_parts = [sum(distances_list[0:i+1]) for i in range(len(distances_list))]

    altitudes = []
    for x in range(chart_width):
        altitudes.append([])
    
    for i,el in enumerate(elevations_lists):
        dist = distances_list[i]
        accrued_distance = 0 if i == 0 else cumulated_distances_parts[i-1]

        # elevation list with draw on these distances
        d_start = accrued_distance
        d_stop = accrued_distance + dist
                
        # elevation list with draw between those pixels
        x_start = int(chart_width * d_start / total_distance_in_meters)
        x_stop = int(chart_width * d_stop / total_distance_in_meters)

        if x_stop < chart_width:
            x_stop += 1 # for 2 altitudes on same x

        el_altitudes = [0]*(x_stop-x_start)
        
        x_el = accrued_distance / total_distance_in_meters * chart_width # el starts at x_el
        x_el = int(x_el)
        
        for x in range(x_stop - x_start):
            el_index = x / (x_stop-x_start) * len(el)    
            a = el[int(el_index)]
            el_altitudes[x] = a
        
        el_altitudes = smooth_altitudes(el_altitudes, distances_list[i])
        
        for i,a in enumerate(el_altitudes):
            altitudes[x_el + i].append(a)
    
    return altitudes

def draw_elevation_chart(c, elevations_lists, distances_list, CHART_LEFT, CHART_BOTTOM, chart_width = 200, chart_height = 140):

    chart_width = int(chart_width)
    
    total_distance_in_meters = sum(distances_list)

    altitudes = altitudes_from_elevations_lists(elevations_lists, distances_list, chart_width)
    
    assert(len(altitudes) == chart_width)
    
    total_distance_km = total_distance_in_meters / 1000
        
    # Define the chart area without padding on the x-axis and with smaller padding on the y-axis
    
    margin_left = 50
    margin_bottom = 100
    y_padding = 0.05 * chart_height  # Smaller padding on the y-axis (5%)

    # Create a Drawing object
    drawing = Drawing(chart_width, chart_height)
    
    # Draw x and y axes without x-axis padding
    drawing.add(Line(0, 0, chart_width, 0, strokeWidth=0.5, strokeColor=colors.black))  # x-axis
    drawing.add(Line(0, 0, 0, chart_height, strokeWidth=0.5, strokeColor=colors.black))  # y-axis

    all_altitudes = [item for sublist in altitudes for item in sublist]

    max_altitude = max(all_altitudes)
    min_altitude = min(all_altitudes)
    altitude_range = max_altitude - min_altitude
    if altitude_range == 0:
        altitude_range = 1
    
    scaled_points = []
    
    # Collect points for the PolyLine and for the filled profile
    profile_points = []
    for x, alts in enumerate(altitudes):
        #print("*", x, alts)
        for alt in alts:
            y = y_padding + (alt - min_altitude) / altitude_range * (chart_height - 2 * y_padding)
            scaled_points.append((x, y))
            profile_points.append((x, y))  # Points for filling the profile

    # Add the baseline points to close the polygon for the filled area
    profile_points.append((chart_width, y))
    profile_points.append((chart_width, 0))  # Bottom-right corner of the chart
    profile_points.append((0, 0))  # Bottom-left corner of the chart

    # Flatten the profile_points list into a flat list of coordinates for the Polygon
    flat_profile_points = [coord for point in profile_points for coord in point]
    
    # Draw the filled profile (light gray)
    drawing.add(Polygon(flat_profile_points, fillColor=colors.lightgrey, strokeWidth=0.5, strokeColor=colors.black))
    
    # Draw the smoothed elevation profile (using y_extra_smooth) as a PolyLine on top of the filled area
    drawing.add(PolyLine(scaled_points, strokeColor=colors.black, strokeWidth=0.5))
    
    # Choose a tick interval that is a multiple of 1, 2, 5, or 10 km
    tick_interval_km = select_tick_interval(total_distance_km)
    
    # Draw tick marks and labels for each tick
    current_km = 0
    while current_km <= total_distance_km:  # Ensure no tick is beyond the chart
        x_position = current_km / total_distance_km * chart_width  # Calculate x position for each tick
        
        # Ensure tick labels are within bounds
        if x_position > 0 and x_position <= chart_width:
            drawing.add(Line(x_position, 0, x_position, -5, strokeWidth=0.5, strokeColor=colors.black))  # Tick mark
            s = String(x_position, -15, f"{current_km}", textAnchor='middle')
            s.fontName = "Helvetica"
            s.fontSize = 10            
            drawing.add(s)
        current_km += tick_interval_km
    
    # draw split for combined activities
    x_splits = [x for x,alts in enumerate(altitudes) if len(alts) == 2]
    for x in x_splits:
        dashed_line = Line(x, 0, x, chart_height, strokeWidth=0.5, strokeColor=colors.black)
        dashed_line.strokeDashArray = [3, 2]  # Dash pattern: [dash length, gap length]
        drawing.add(dashed_line)
    
    # Add ticks on the y-axis (elevation) ensuring they stay within bounds
    y_ticks = select_y_ticks(min_altitude, max_altitude)
    for tick in y_ticks:
        y_position = y_padding + (tick - min_altitude) / altitude_range * (chart_height - 2 * y_padding)  # Calculate y position for each tick
        if 0 <= y_position <= chart_height:  # Ensure y ticks are within the chart bounds
            drawing.add(Line(0, y_position, -5, y_position, strokeWidth=0.5, strokeColor=colors.black))  # Tick mark
            s = String(-10, y_position - 3, f"{int(tick)}", textAnchor='end')
            s.fontName = "Helvetica"
            s.fontSize = 10            
            drawing.add(s)

    renderPDF.draw(drawing, c, CHART_LEFT, CHART_BOTTOM)
    
if __name__ == "__main__":
    # Example usage with dummy data:
    altitudes_1 = [1000, 1200, 1300, 1100, 1600, 1300, 1200, 1500]
    altitudes_2 = [2000, 1600, 1800, 1700, 1400]
    altitudes_3 = [1000, 1200, 1500, 1400, 1400, 1300, 1200, 1200]
    distances_list = [2000, 1500, 1000] # Distances in meters

    from reportlab.pdfgen import canvas
    c = canvas.Canvas("chart.pdf", pagesize=(300, 200))
    draw_elevation_chart(c, [altitudes_1, altitudes_2, altitudes_3], distances_list, 50, 30, chart_width = 200, chart_height = 140)
    c.save()
    