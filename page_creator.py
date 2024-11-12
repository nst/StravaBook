import sys
from datetime import datetime
import locale
import elevation
import os
import elevation_chart
import json
from typing import Dict, List
from collections import namedtuple

#from PIL import Image

import map_maker
import json_utils
import config

from reportlab.lib.pagesizes import letter
from reportlab.graphics import renderPDF
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm, cm

from svglib.svglib import svg2rlg

from collections import namedtuple

locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8") # TODO: config.json

def convert_meters_to_kilometers(meters):
    # Convert meters to kilometers
    kilometers = meters / 1000
    # Format the result to one decimal place
    return f"{kilometers:.1f} Km"

def convert_seconds_to_hms(seconds):
    # Calculate hours, minutes, and remaining seconds
    hours = seconds // 3600
    remaining_seconds = seconds % 3600
    minutes = remaining_seconds // 60
    remaining_seconds = remaining_seconds % 60
    # Format the result as "HH:mm:ss"
    return f"{hours}:{minutes:02}.{remaining_seconds:02}"

def draw_photos(c, page_path, meta):
    
    PHOTOS_PATH = f"{page_path}/photos"
    if not os.path.exists(PHOTOS_PATH):
        return
    
    photos_count = len([f for f in os.listdir(PHOTOS_PATH) if os.path.isfile(os.path.join(PHOTOS_PATH, f)) and f.endswith(".jpg")])

    #print(f"Number of photos: {photos_count}")    
    
    draw_photo_border = True
    if "photo_border" in meta and meta["photo_border"] == False:
        draw_photo_border = False
    
    if photos_count == 1:
        p = f'{page_path}/photos/1.jpg'
        
        if os.path.exists(p):

            file_size_in_mb = os.path.getsize(p) / 1024**2
            if file_size_in_mb < 2:
                print(f"oo> too small: {p} {file_size_in_mb:.2f} MB")


            factor = 0.1733 * 2
            x = 15
            y = 190
            c.drawImage(p, x, y, 1600 * factor, 1200 * factor)
            if draw_photo_border:
                c.rect(x, y, 1600 * factor, 1200 * factor)
        
    if photos_count == 4:
    
        w, h = config.STANDARD_PORTRAIT

        coords = [(15, 402), (w/2 + 4, 402), (15, 190), (w/2 + 4, 190)]
        for i in range(1, 5):
            p = f'{page_path}/photos/{i}.jpg'
            
            if os.path.exists(p):
                
                #file_size_in_mb = os.path.getsize(p) / 1024**2
                #if file_size_in_mb > 2:
                #    print(f"oo> too large: {p} {file_size_in_mb:.2f} MB")
                
                #with Image.open(p) as img:
                #    width, height = img.size
                #    if width != 1600:
                #        print(f"ooo> {width} px: {p}")
                
                factor = 0.17
                x, y = coords[i-1]
                c.drawImage(p, x, y, 1600 * factor, 1200 * factor)
                if draw_photo_border:
                    c.rect(x, y, 1600 * factor, 1200 * factor)

def pretty_date(date_string): # "2024-09-01T14:30:00Z"

    date_object = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")

    if date_object.day == 1:
        day_str = "1er"
    else:
        day_str = str(date_object.day)

    return f"{day_str} {date_object.strftime('%B %Y')}"

def read_layouts(layout_path):
    
    """
    {
        "text": "Mont Blanc",
        "x": 40,
        "y": 60,
        "size": 16,
        "color": "white",
        "italic": true
    }
    """
    
    TextLayout = namedtuple('TextLayout', ['text', 'color', 'size', 'x', 'y', 'italic'])
    
    layouts = json_utils.load(layout_path)
    
    if not layouts:
        return []
    
    return [TextLayout(**l) for l in layouts]

def create_fullpage(aids):
            
    aids_str = [str(aid) for aid in aids]
    joined_aids = str('_'.join(aids_str))

    page_dir    = f"pages/{joined_aids}"
    layout_path = f"{page_dir}/_layout_.json"
    pdf_path    = f"{page_dir}/{joined_aids}.pdf"
    photo_path  = f"{page_dir}/photo.jpg"

    w,h = config.STANDARD_PORTRAIT
    
    c = canvas.Canvas(pdf_path, pagesize=config.STANDARD_PORTRAIT_BLEED)
    c.translate(config.BLEED, config.BLEED)
    
    if os.path.exists(photo_path):
        factor = 0.2
        x = -20
        y = -5
        c.drawImage(photo_path, x, y, 3024 * factor, 4032 * factor)
        #c.rect(x, y, 1600 * factor, 1200 * factor)

    text_layouts = read_layouts(layout_path)

    for tl in text_layouts:
        print(">>", tl)
        color = colors.black
        if tl.color == "white":
            color = colors.white
        
        c.setFillColor(color)
        print("------------->", tl.size)
        c.setFont("Times-Roman", tl.size)
        c.drawCentredString(tl.x, tl.y, tl.text)

    c.showPage()
    c.save()

def create_page(aids):

    print("--", aids)
    
    if type(aids[0]) == str:
        return create_fullpage(aids)
    
    aids_str = [str(aid) for aid in aids]
    joined_aids = str('_'.join(aids_str))

    page_dir      = f"pages/{joined_aids}"
    activity_path = f"{page_dir}/{joined_aids}_processed.json"
    pdf_path      = f"{page_dir}/{joined_aids}.pdf"
    
    
    """
    Courier
    Courier-Bold
    Courier-BoldOblique
    Courier-Oblique
    Helvetica
    Helvetica-Bold
    Helvetica-BoldOblique
    Helvetica-Oblique
    Symbol
    Times-Bold
    Times-BoldItalic
    Times-Italic
    Times-Roman
    ZapfDingbats
    """
    
    a = json_utils.load(activity_path)
    
    if not a:
        print(f"-- ERROR: json file for activity is missing: {aids}")
        sys.exit(1)
    
    meta = json_utils.load_meta_for_aids(aids)
    a["name"] = meta["Titre"]    
    name = a["name"]
    place_name = a["place_name"] if "place_name" in a else None
    polyline = a["polyline"]
    
    if "place_name" in meta:
        place_name = meta["place_name"] # for 9062353745 Marrakech
    
    c = canvas.Canvas(pdf_path, pagesize=config.STANDARD_PORTRAIT_BLEED)
    c.setLineWidth(0.5)
    c.translate(config.BLEED, config.BLEED)
    c.setFont("Times-Bold", 24)
    
    # Draw name
    w,h = config.STANDARD_PORTRAIT
    c.drawCentredString(w / 2, h-35, name)

    # show elevation
    show_chart = True

    if show_chart:
        
        elevations_list = []
        for aid in aids:
            print("----->", aid)
            single_activity = json_utils.load(f"{page_dir}/{aid}.json")
            e = elevation.get_elevations(single_activity["polyline"], joined_aids, aid)
            if not e or len(e) == 0:
                show_chart = False
                print(f"-- no elevation for {aid}")
                break                
            elevations_list.append(e)
        
        distances_list = []
        
        for aid in aids:
            #print("-----------", aid, f"{page_dir}/{aid}.json")
            
            single_activity = json_utils.load(f"{page_dir}/{aid}.json")
            distances_list.append(single_activity["distance"])

    if show_chart:
        
        elevation_chart.draw_elevation_chart(c, elevations_list, distances_list, CHART_LEFT = 50, CHART_BOTTOM = 628, chart_width = w / 2 - 53, chart_height = 75)
    
    c.setFont("Helvetica", 12)
        
    if "override_date" in meta:
        date_str = meta["override_date"]
    else:
        date_str = pretty_date(a["start_date_local"])

    s = f"{date_str}, {place_name}" if place_name else f"{date_str}"
    
    c.drawCentredString(w / 2, 713, s)

    c.setFont("Helvetica", 14)

    drawing = svg2rlg("icons/distance.svg")
    drawing.scale(0.022, 0.022)
    renderPDF.draw(drawing, c, 298, 680-4)

    distance_str = convert_meters_to_kilometers(a["distance"])
    c.drawRightString(380, 680, distance_str)

    drawing = svg2rlg("icons/elevation.svg")
    drawing.scale(0.025, 0.025)
    renderPDF.draw(drawing, c, 388, 680-4)

    d_plus = round(a['total_elevation_gain'])
    elevation_str = f"{d_plus} D+"
    c.drawRightString(463, 680, elevation_str)

    drawing = svg2rlg("icons/time.svg")
    drawing.scale(0.022, 0.022)
    renderPDF.draw(drawing, c, 486, 680-4)

    duration_str = convert_seconds_to_hms(int(a["elapsed_time"]))
    c.drawRightString(560, 680, duration_str)

    #
    
    y = 649
    
    subitems_count = 0
    
    #
    
    comments = meta["Comments"] if "Comments" in meta else []
    if not comments:
        comments = []
     
    if len(comments) != 0:
        for com in comments:
            if subitems_count == 2:
                break
            c.drawString(300, y, com)
            y -= 20
            subitems_count += 1
    
    #
    
    if len(comments) == 0:
        
        IndexEntry = namedtuple('IndexEntry', ['name', 'icon'])
        
        index_entries = (
            IndexEntry("Sommets", "icons/summit.svg"),
            IndexEntry("Cabanes", "icons/hut.svg")
            #IndexEntry("Bisses", "icons/bisse.svg")
        )
        
        for ie in index_entries:
        
            for s in meta[ie.name]:
                #print(s)
                if subitems_count == 2:
                    break
                drawing = svg2rlg(ie.icon)
                drawing.scale(0.018, 0.018)
                y_pic = y-4
                #print(ie.icon)
                if ie.icon == "icons/hut.svg":
                    y_pic += 3
                renderPDF.draw(drawing, c, 298, y_pic)
                c.drawString(320, y, s)
                y -= 20
                subitems_count += 1

    #
    
    draw_photos(c, page_dir, meta)
    
    #

    if False:
        sid = str(a["id"])
        url = f"https://www.strava.com/activities/{joined_aids}"
        c.linkURL(url, (0, h-20, 250, h), relative=1)
        c.rect(0, h-20, 250, h)
        c.drawString(0, h-10, f"Strava ID: {joined_aids}")
    
    # map
    
    map_x = -1 * mm
    map_y = -1 * mm
    map_w = w + 2*mm
    map_h = 182 + 1*mm
    
    map_path = map_maker.map_file_path(aids)
    if os.path.exists(map_path):
        c.drawImage(map_path, map_x, map_y, map_w, map_h)
        c.line(map_x, map_y+map_h, map_x+map_w, map_y+map_h)
            
    # Save the page
    c.showPage()
    c.save()
    
    start_date = a["start_date_local"]
    print(f"-- save {pdf_path} | {start_date} | {name}")

if __name__ == "__main__":
    
    print("-")
