import json
from typing import Dict, List
import logging
import os

from PyPDF2 import PdfWriter, PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm, cm

# https://pdf-to-book.bookfactory.ch/fr

# gs -o book_print.pdf -sDEVICE=pdfwrite -dEmbedAllFonts=true -dPDFSETTINGS=/prepress book.pdf

# gs -o book_print.pdf -sDEVICE=pdfwrite -dEmbedAllFonts=true -dPDFSETTINGS=/prepress -dDownsampleColorImages=false -dDownsampleGrayImages=false -dDownsampleMonoImages=false -dColorImageResolution=300 -dGrayImageResolution=300 -dMonoImageResolution=1200 book.pdf

import argparse

from multiprocessing import Pool

from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import polyline

import json_utils
import config
import geocoding

from reportlab.lib import colors

import index_creator
import map_maker
import page_creator

pdfmetrics.registerFont(TTFont('Helvetica', '/System/Library/Fonts/Helvetica.ttc'))
pdfmetrics.registerFont(TTFont('Times',     '/System/Library/Fonts/Times.ttc'))

from collections import namedtuple
Tag = namedtuple('Tag', ['text', 'color'])

# TODO: cover: photos Dérupe 4 saisons | 1h

# Constants
ACTIVITIES_CLEAN_FILE = "activities_clean.json"
ACTIVITIES_IDS_FILE = "activities_ids.json"
ACTIVITIES_IDS_FILE_TEST = "activities_ids_test.json"
#PAGES_DIR = "pages"
OUTPUT_FILE = "book.pdf"
INDEX_PDF = "index.pdf"

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def merge_activities(activities):
    
    activities.sort(key=lambda a:a["start_date_local"])

    d = activities[0]
    
    for a in activities[1:]:
        d["name"] += " / " + a["name"]
        d["distance"] += a["distance"]
        d["elapsed_time"] += a["elapsed_time"]
        d["total_elevation_gain"] += a["total_elevation_gain"]
        
    coords = []
    elevations_lengths = []

    for a in activities:
    
        p = a["polyline"]
        c = polyline.decode(p)
        coords.extend(c)
        elevations_lengths.append(len(c))

        #print("--> ", a["id"])
        #print("--> ", a["name"])
        #print("--> ", len(c))
    
    if len(coords) > 0:
        d["polyline"] = polyline.encode(coords)
    
    #activities.sort(key=lambda a:a["id"])
    ids = [str(a["id"]) for a in activities]
    d["id"] = '_'.join(ids)
    
    d["elevations_lengths"] = elevations_lengths # used to draw split line on charts of combined activities
        
    return d

def prepare_files_structure(activities, activity_ids) -> None:

    #print("----------------------------------------------------->", activity_ids)

    for aids in activity_ids:
    
        #print("*********** aids:", aids)

        joined_aids = '_'.join([str(aid) for aid in aids])
                
        dir_path = f"{config.PAGES_DIR}/{joined_aids}"
        
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            print("-------------------------------", dir_path)

        #print("--- dir_path:", dir_path)
        
        matched_activities = [d for d in activities if d["id"] in aids]
        
        if not matched_activities or len(matched_activities) == 0:
            continue # eg. full page
        
        for a in matched_activities:
            # save original activities
            aid = a["id"]
            original_activity_path = f"{dir_path}/{aid}.json"
            if not os.path.exists(original_activity_path):
                json_utils.dump(a, original_activity_path)

        names = [d["name"] for d in matched_activities]
        names_string = " / ".join(names)
    
        activity_file = f"{config.PAGES_DIR}/{joined_aids}/{joined_aids}_processed.json"
        if not os.path.exists(activity_file):
            a = merge_activities(matched_activities)
            
            place_name = geocoding.fetch_geo(aids)
            if place_name:
                a["place_name"] = place_name
            
            json_utils.dump(a, str(activity_file))
            logging.info(f"Wrote activity {joined_aids} {names_string}")
        
        meta = json_utils.load_meta_for_aids(aids)
        
        if not meta:
        
            meta = {
                "Titre": names_string,
                "Sommets": [],
                "Cabanes": [],
                "Region": None,
                "Comments": None
            }
            json_utils.dump_meta(meta, aids)
        
        #if meta:            
        #    meta.pop("Bisses")
        #    json_utils.dump_meta(meta, aids)

def create_pdf_pages(activity_ids, use_cache=False, index_only=False, use_parallelism=True):
        
    page_for_aids = {}
        
    for i,aids in enumerate(activity_ids):
        
        aids_str = [str(aid) for aid in aids]
        joined_aids = str('_'.join(aids_str))
        
        page_for_aids[joined_aids] = i+1 # starts at page 1
        
    if not use_cache and not index_only:
        
        if use_parallelism:
            with Pool() as pool:
                results = pool.map(page_creator.create_page, activity_ids)
        else:
            for aids in activity_ids:
                page_creator.create_page(aids)            
        
    return page_for_aids

def add_tag(c, tag, top_right=False):

    if not tag:
        return
    
    c.saveState()

    y = 715
    w = 60
    h = 26

    if top_right:
        x = 500
        rotate_angle = -30
    else:
        x = 15
        rotate_angle = 30    

    # Translate and rotate for the tag
    c.translate(x + w/2, y + h/2)  # Move the origin to the center of the tag
    c.rotate(rotate_angle)  # Rotate 30 degrees counterclockwise
    
    # Move back the origin for drawing the rectangle
    c.translate(-w / 2, -h / 2)

    # Draw the tag - a rounded rectangle
    c.setFillColor(tag.color)
    corner_radius = 10
    c.roundRect(0, 0, w, h, corner_radius, fill=1)
    
    # Set the font and size for the label
    c.setFont("Helvetica-Bold", 14) # macOS
    c.setFillColor(colors.white)
    
    # Label the tag with the provided text
    c.drawCentredString(w / 2, h / 2 - 4, tag.text)
    
    # Restore the canvas state
    c.restoreState()

def draw_cut_marks(c, page_width, page_height, bleed):

    t = 0.15 * cm

    c.saveState()

    c.setLineWidth(0.5)

    c.setStrokeColorRGB(1, 0, 0)  # Set the color for cut marks
    
    c.translate(-bleed, -bleed)
    
    # bottom left
    c.line(0, bleed, t, bleed) # -
    c.line(bleed, 0, bleed, t) # |

    # bottom right
    c.line(page_width, bleed, page_width - t, bleed) # -
    c.line(page_width - bleed, 0, page_width - bleed, t) # |

    # top left
    c.line(0, page_height - bleed, t, page_height - bleed) # -
    c.line(bleed, page_height, bleed, page_height - t) # |

    # top right
    c.line(page_width - t, page_height - bleed, page_width, page_height - bleed) # -
    c.line(page_width - bleed, page_height, page_width - bleed, page_height - t) # |
    
    c.restoreState()

def add_page_number_and_tags(page, number, squared, tags):

    packet = BytesIO()
    
    bleed = 3 * mm  # Bleed amount (3 mm) ("fond perdu")
    (w,h) = config.STANDARD_PORTRAIT_BLEED
    c = canvas.Canvas(packet, pagesize=(w, h))

    #c.bookmarkPage(str(number))  # Create a named destination

    c.setLineWidth(0.5)
    c.translate(bleed, bleed)

    c.setFont("Helvetica", 10)
    
    is_odd_page = number % 2 == 0
    
    if is_odd_page == 0:
        x_position = w - 60
    else:
        x_position = 40
    
    y_position = 20

    if squared:
        c.setFillColor(colors.white)
        c.rect(x_position - 10, y_position - 5, 20, 15, stroke=1, fill=1)
    c.setFillColor(colors.black)
    c.drawCentredString(x_position, y_position, str(number))

    if tags and len(tags) >= 1:
        add_tag(c, tags[0], top_right= not is_odd_page)
    if tags and len(tags) == 2:
        add_tag(c, tags[1], top_right= is_odd_page) 

    draw_cut_marks(c, w, h, bleed)
    
    c.save()
    packet.seek(0)
    new_pdf = PdfReader(packet)
    page.merge_page(new_pdf.pages[0])
    return page

def create_empty_page(empty_page_path):

    c = canvas.Canvas(empty_page_path, pagesize=config.STANDARD_PORTRAIT_BLEED)
    c.showPage()
    c.save()
    
def assemble_pages(activity_ids: List[List[int]], index_only=False) -> None:
    pdf_writer = PdfWriter()
    page_number = 0
    
    print("-- index_only", index_only)
    
    if not index_only:

        for aids in activity_ids:
            aids_str = [str(aid) for aid in aids]
            joined_aids = str('_'.join(aids_str))
    
            page_path = f"{config.PAGES_DIR}/{joined_aids}/{joined_aids}.pdf"
            if not os.path.exists(page_path):
                logging.warning(f"Missing page_path {page_path}")
                continue
            
            # read meta, use proper tag
            meta = json_utils.load_meta_for_aids(aids)
            tags = []

            if meta:
            
                if "Course" in meta and meta["Course"] == True:
                    tags.append(Tag(text="Course", color=colors.red))
                if "Trail" in meta and meta["Trail"] == True:
                    tags.append(Tag(text="Trail", color=colors.green))
                
            pdf_reader = PdfReader(str(page_path))
            page = pdf_reader.pages[0]
            page_number += 1
            
            if type(aids[0]) == str:
                pdf_writer.add_page(page)
            else:
                numbered_page = add_page_number_and_tags(page, page_number, squared=True, tags=tags)
                pdf_writer.add_page(numbered_page)
        
    if os.path.exists(INDEX_PDF):
        index_reader = PdfReader(INDEX_PDF)
        for page in index_reader.pages:
            page_number += 1
            numbered_page = add_page_number_and_tags(page, page_number, squared=False, tags=None)
            pdf_writer.add_page(numbered_page)
    
    # make sure number of pages is a multiple of 4
    
    PAGES_MULTIPLE = 4
    
    filename = "empty.pdf"
    create_empty_page(filename)
    for i in range(PAGES_MULTIPLE - (page_number % PAGES_MULTIPLE)):
        empty_reader = PdfReader(filename)
        print(f"-- {i} add page")
        for page in empty_reader.pages: # only one page
            page_number += 1
            numbered_page = add_page_number_and_tags(page, page_number, squared=False, tags=None)
            pdf_writer.add_page(numbered_page)
    
    with open(OUTPUT_FILE, 'wb') as output_stream:
        pdf_writer.write(output_stream)

    logging.info(f"Successfully created {OUTPUT_FILE} with {page_number} numbered pages.")

def main():
    activities = json_utils.load(ACTIVITIES_CLEAN_FILE)
    
    parser = argparse.ArgumentParser(description="book.py options")
    parser.add_argument('-s', '--sequential', action='store_true', help="Sequential (no parallelism)")
    parser.add_argument('-t', '--use_test_data', action='store_true', help="Use a subset of activities")
    parser.add_argument('-i', '--index_only', action='store_true', help="Generate only index")
    parser.add_argument('-c', '--cache_for_pages', action='store_true', help="Don't regenerate existing pages")
    parser.add_argument('-o', '--open', action='store_true', help="Open result file")
    parser.add_argument('-p', '--page', type=int, help="Open activity for page")
    parser.add_argument('-d', '--directory', type=str, help="Open directory")
    args = parser.parse_args()
    
    print("--", args)
    
    if args.directory:
        os.system(f"open {config.PAGES_DIR}/{args.directory}/_meta_.json")
        return
    
    if args.page:
        page_for_ids = json_utils.load("page_for_ids.json")
        
        if not page_for_ids:
            print("-- no page_for_ids.json")
            return
            
        for k,v in page_for_ids.items():
            if args.page == v:
                os.system(f"open {config.PAGES_DIR}/{k}/photos/")
                return

        print(f"-- no id found for page {args.page}")
        return
    
    if args.use_test_data:
        activity_ids = json_utils.load(ACTIVITIES_IDS_FILE_TEST)
    else:
        activity_ids = json_utils.load(ACTIVITIES_IDS_FILE)
    
    prepare_files_structure(activities, activity_ids)
    
    for aids in activity_ids:
        if type(aids[0]) == str:
            print("** fullpage:", aids)
            continue
        map_maker.get_map(aids)
    
    page_for_ids = create_pdf_pages(activity_ids, use_cache = args.cache_for_pages, index_only = args.index_only, use_parallelism=not args.sequential)
    
    json_utils.dump(page_for_ids, "page_for_ids.json")
    
    index_entries = index_creator.create_index(activity_ids, page_for_ids)
    index_creator.generate_pdf_index(index_entries, INDEX_PDF)

    assemble_pages(activity_ids, index_only = args.index_only)
    
    if args.open:
        os.system(f"/usr/bin/open {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
    
    """
    # Get the list of available fonts
    available_fonts = c.getAvailableFonts()

    # Print the available fonts
    print("Available fonts in ReportLab's Canvas:")
    for font in available_fonts:
        print(font)

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
