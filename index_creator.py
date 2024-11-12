import re

from svglib.svglib import svg2rlg

import reportlab
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Flowable, PageBreak, Image
from reportlab.graphics import renderPDF
from reportlab.lib.colors import black

import config
import json_utils

def split_summit_and_altitude(s):
    # The regex pattern matches any text (summit name), 
    # optionally followed by a number and 'm' for altitude
    pattern = r"^(.*?)\s*(\d{1,5}\s*m)?$"
    match = re.match(pattern, s.strip())
    
    if match:
        summit_name = match.group(1).strip()  # The summit name part
        altitude = match.group(2).strip() if match.group(2) else None  # The altitude part (if it exists)
        return summit_name, altitude
    return None, None

# Custom class to align page number to the right with proper vertical spacing
class AlignedText(Flowable):
    def __init__(self, left_text, right_text, page_width, line_height=12):
        Flowable.__init__(self)

        summit, altitude = split_summit_and_altitude(left_text)

        if summit and altitude:        
            self.left_text = summit
            self.middle_text = altitude
        else:
            self.left_text = left_text
            self.middle_text = None
            
        self.right_text = right_text
        self.page_width = page_width
        self.line_height = line_height

    def draw(self):
        # Draw left text (title)
        self.canv.drawString(40, 0, self.left_text)
        
        # Calculate the width of the right text (page number)

        if self.middle_text:
            text_width = self.canv.stringWidth(self.middle_text, "Helvetica", 12)
            self.canv.drawString(self.page_width - 300 - text_width, 0, self.middle_text)
        
        # Draw right text (page number) aligned to the right
        text_width = self.canv.stringWidth(self.right_text, "Helvetica", 12)
        self.canv.drawString(self.page_width - 200 - text_width, 0, self.right_text)
                
    def wrap(self, *args):
        # Define the height of the flowable (line height for each entry)
        return self.page_width, self.line_height

class SVGFlowable(Flowable):
    def __init__(self, svg_path, x_scale, y_scale, x, y, framed):
        Flowable.__init__(self)
        self.drawing = svg2rlg(svg_path)
        if not self.drawing:
            import sys
            print(f"-- can't build drawing for {svg_path}")
            sys.exit(1)
        self.drawing.scale(x_scale, y_scale)  # Scale the drawing
        self.x_scale = x_scale
        self.y_scale = y_scale
        self.x = x
        self.y = y
        self.framed = framed

    def draw(self):
        renderPDF.draw(self.drawing, self.canv, self.x, self.y)  # Adjust position as needed

        if self.framed:
            width = self.drawing.width * self.x_scale
            height = self.drawing.height * self.y_scale
            self.canv.setStrokeColor(black)  # Set frame color
            self.canv.setLineWidth(0.5)
            self.canv.rect(self.x, self.y, width, height, stroke=1, fill=0)  # Draw the frame

def sort_index_data(index_data):
    
    sorted_index = []
    
    categories = ["Sommets", "Cabanes", "Courses", "Trails"]
    regions = ["Bas Valais - Nord", "Bas Valais - Sud", "Valais Central - Nord", "Valais Central - Sud", "Haut Valais - Nord", "Haut Valais - Sud"]
    ch = ["Berne", "Fribourg", "Jura", "Vaud", "Tessin"]
    countries = ["France", "Italie", "Maroc", "Norvège", "Écosse", "Londres", "Tenerife"]
    
    index_sections = categories + regions + ch + countries
    
    for section in index_sections:
        
        if not section in index_data:
            continue
        
        pages_for_place = index_data[section]
        
        sorted_places = sorted(pages_for_place.keys())
        
        l = [(place, pages_for_place[place]) for place in sorted_places]

        sorted_index.append((section, l))

    return sorted_index

def pretty_print_ids_for_page(page_for_ids):
    
    page_and_id = [(pages, i) for i, pages in page_for_ids.items()]
    
    for (p, i) in page_and_id:
        print(f"-- {p}, {i}")    

def create_index(activity_ids, page_for_ids):
    
    pretty_print_ids_for_page(page_for_ids)
    
    index_entries = {"Sommets": {}, "Cabanes": {}, "Courses": {}, "Trails":{}}

    for aids in activity_ids:

        aids_str = [str(aid) for aid in aids]
        joined_aids = str('_'.join(aids_str))

        meta = json_utils.load_meta_for_aids(aids)
        if not meta:
            continue
        
        for category in ["Sommets", "Cabanes"]:
            for item in meta[category]:
                if not item in index_entries[category]:
                    index_entries[category][item] = []
                
                page_number = page_for_ids[joined_aids] if joined_aids in page_for_ids else "?"
                index_entries[category][item].append(page_number)
        
        #
        
        if "Region" in meta:
            region = meta["Region"]
            title = meta["Titre"]
                        
            if region not in index_entries:
                index_entries[region] = {}
            
            page_number = page_for_ids[joined_aids] if joined_aids in page_for_ids else "?"
            if not title in index_entries[region]:
                index_entries[region][title] = []
            index_entries[region][title].append(page_number)
            
        else:
            print(f"-- no region for {aids}", meta["Titre"])
        
        #
        
        for cat in ["Course", "Trail"]:
        
            if cat in meta and meta[cat] == True:
                title = meta["Titre"]
                page_number = page_for_ids[joined_aids] if joined_aids in page_for_ids else "?"
                index_entries[cat+"s"][title] = [page_number]
    
    #print("--", index_entries)
    
    sorted_index  = sort_index_data(index_entries)
    
    return sorted_index

def generate_pdf_index(data, file_name):
    
    images_for_section = {
        "Sommets"  :("icons/summit.svg",   0.02, 0.02, -20, 7, False),
        "Cabanes"  :("icons/hut.svg",      0.02, 0.02, -20, 7, False),
        #"Bisses"   :("icons/bisse.svg",    0.02, 0.02, -20, 7, False),
        "Trails"   :("icons/trail.svg",    0.02, 0.02, -20, 7, False),
        "Courses"  :("icons/course.svg",   0.02, 0.02, -20, 7, False),
        "Maroc"    :("icons/morocco.svg",  0.05, 0.05, -30, 7, False), # https://uxwing.com/morocco-flag-icon/
        "Italie"   :("icons/italy.svg",    0.28, 0.28, -30, 7, False),
        "Écosse"   :("icons/scotland.svg", 0.05, 0.05, -30, 7, False),
        "France"   :("icons/france.svg",   0.05, 0.05, -30, 7, False),
        "Espagne"  :("icons/spain.svg",    0.05, 0.05, -30, 7, False),
        "Norvège"  :("icons/norway.svg",   0.12,  0.12,  -30, 7, False),
        "Londres"  :("icons/uk.svg",       0.45,  0.45,  -30, 7, False),
        "Tenerife" :("icons/spain.svg",    0.05, 0.05, -30, 7, False),
        "Berne"    :("icons/bern.svg",     0.05, 0.05, -30, -4, True),
        "Fribourg" :("icons/fribourg.svg", 0.04, 0.04, -30, -4, True),
        "Jura"     :("icons/jura.svg",     0.07, 0.07, -30, -4, True),
        "Vaud"     :("icons/vaud.svg",     0.05, 0.05, -30, -4, True),
        "Tessin"  :("icons/ticino.svg",    0.05, 0.05, -30, -4, True),
        "Valais Central - Nord" :("icons/valais.svg", 0.05, 0.05, -30, -4, True),
        "Valais Central - Sud"  :("icons/valais.svg", 0.05, 0.05, -30, -4, True),
        "Bas Valais - Nord"     :("icons/valais.svg", 0.05, 0.05, -30, -4, True),
        "Bas Valais - Sud"      :("icons/valais.svg", 0.05, 0.05, -30, -4, True),
        "Haut Valais - Nord"    :("icons/valais.svg", 0.05, 0.05, -30, -4, True),
        "Haut Valais - Sud"     :("icons/valais.svg", 0.05, 0.05, -30, -4, True)
    }

    doc = SimpleDocTemplate(file_name, pagesize=config.STANDARD_PORTRAIT_BLEED)
    
    elements = []
    
    styles = getSampleStyleSheet()
    
    #styles['Heading2'].fontSize = 10
    
    page_width, _ = config.STANDARD_PORTRAIT_BLEED
    
    elements.append(Paragraph("Index", styles['Title']))
    elements.append(Spacer(1, 12))

    for cat, l in data:

        if cat == "Bas Valais - Nord":
            #elements.append(Spacer(1, 24))
            image_width = 500
            image = Image("images/valais.png", width=image_width, height=image_width*0.725)
            elements.append(image)
        
        elements.append(Paragraph(cat, styles['Heading2']))

        if cat in images_for_section:
            svg_path, x_scale, y_scale, x, y, framed = images_for_section[cat]
            elements.append(SVGFlowable(svg_path, x_scale, y_scale, x, y, framed))

        for place, pages in l:
            
            page_numbers = ', '.join([str(p) for p in pages])
            
            elements.append(AlignedText(place, page_numbers, page_width, line_height=14))
        
        if cat in ["Sommets", "Cabanes", "Courses", "Trails"]: # , "Bas Valais - Nord"
            elements.append(PageBreak())

        #if cat == "Bisses":
        #    break
            
    doc.build(elements)
