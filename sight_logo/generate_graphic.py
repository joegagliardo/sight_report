import os
import sys
print(f"Using interpreter: {sys.executable}")

from PIL import Image, ImageDraw, ImageFont, ImageOps

def generate_trip_infographic(data):
    # --- Configuration & Constants ---
    width = 1200
    row_height = 400
    header_height = 250
    bg_color = "#0D2B63"  # Dark Navy
    bright_blue = "#4DA6FF"
    white = "#FFFFFF"
    black = "#000000"
    
    classes = data.get("classes", [])
    num_classes = len(classes)
    
    # Calculate rows based on the provided logic
    # (Simplified logic: splits into rows of 3 to balance as requested)
    rows = []
    for i in range(0, num_classes, 3):
        rows.append(classes[i:i + 3])
    
    total_height = header_height + (len(rows) * row_height) + 100
    img = Image.new('RGB', (width, total_height), color=white)
    draw = ImageDraw.Draw(img)

    # Load Fonts (Assumes standard paths, adjust for your OS)
    try:
        font_bold = ImageFont.truetype("arialbd.ttf", 24)
        font_reg = ImageFont.truetype("arial.ttf", 18)
        font_large = ImageFont.truetype("arialbd.ttf", 40)
    except:
        font_bold = font_reg = font_large = ImageFont.load_default()

    # --- 1. Header Construction ---
    # Draw Google Cloud Icon Placeholder & "TRIP Report"
    draw.text((50, 40), "☁ TRIP Report", fill=black, font=font_large)
    
    # Draw Company Logo (Mocking the 1/3 scale rule)
    # company_logo = Image.open(f"company_logos/{data['company']}.jpg")
    # img.paste(company_logo, (50, 110))

    # --- 2. Dark Blue Section ---
    draw.rectangle([0, header_height - 50, width, total_height], fill=bg_color)
    draw.text((50, header_height - 30), "Completed PLLJ Training Overview", fill=white, font=font_bold)
    draw.text((50, header_height + 10), data["company"], fill=bright_blue, font=font_large)

    # --- 3. Timeline Rows ---
    current_y = header_height + 150
    card_w = 240
    margin = 50
    padding = (card_w // 2) + margin
    items_per_row = 3
    content_width = width - (2 * padding)
    
    # Calculate fixed step based on max items per row for vertical alignment
    if items_per_row > 1:
        fixed_step = content_width / (items_per_row - 1)
    else:
        fixed_step = 0

    for row in rows:
        num_in_row = len(row)
        
        # Calculate x-positions using the fixed step
        x_positions = [int(padding + (i * fixed_step)) for i in range(num_in_row)]

        # Draw horizontal timeline line for the items in this row
        if num_in_row > 1:
            draw.line([(x_positions[0], current_y), (x_positions[-1], current_y)], fill=bright_blue, width=3)
        elif num_in_row == 1:
            # For a single item, draw a small horizontal stub or just the vertical connector
            pass

        for i, entry in enumerate(row):
            x = x_positions[i]
            
            # Vertical connector
            draw.line([(x, current_y - 40), (x, current_y + 40)], fill=bright_blue, width=3)

            # --- Date Pill (Above) ---
            pill_w, pill_h = 140, 50
            draw.rounded_rectangle([x - pill_w//2, current_y - 90, x + pill_w//2, current_y - 40], 
                                   radius=20, fill="#345491")
            draw.text((x - 45, current_y - 75), entry['date'], fill=white, font=font_reg)

            # --- Course Card (Below) ---
            card_w, card_h = 240, 180
            card_top = current_y + 40
            draw.rounded_rectangle([x - card_w//2, card_top, x + card_w//2, card_top + card_h], 
                                   radius=15, fill="#2A4A8E")
            
            # Course Title
            draw.text((x - card_w//2 + 15, card_top + 10), entry['title'], fill=white, font=font_bold)
            
            # Instructor Placeholder (Circle)
            draw.ellipse([x - 100, card_top + 60, x - 50, card_top + 110], fill="#CCCCCC")
            
            # Instructor Name (Split)
            name_parts = entry['instructor'].split(' ')
            draw.text((x - 40, card_top + 65), name_parts[0], fill=white, font=font_reg)
            draw.text((x - 40, card_top + 85), name_parts[1], fill=white, font=font_reg)

            # Attendees (Bottom of card)
            draw.text((x - 40, card_top + 130), f"👤 {entry['attendees']}", fill=white, font=font_bold)

        current_y += row_height

    # --- 4. Footer ---
    draw.text((50, total_height - 60), "🌐 ROI Training", fill=white, font=font_bold)

    # Save Output
    output_path = "trip_infographic_output.png"
    img.save(output_path)
    print(f"Infographic generated: {output_path}")

# --- Example Usage ---
example_data = {
    "company": "Rackspace",
    "classes": [
        {"date": "Jan 1, 2026", "instructor": "Joey Gagliardo", "title": "App Dev with LLM", "attendees": 15},
        {"date": "Feb 1, 2026", "instructor": "Joey Gagliardo", "title": "Google ADK", "attendees": 20},
        {"date": "Mar 1, 2026", "instructor": "Doug Rehnstrom", "title": "Gemini Workspace", "attendees": 9},
        {"date": "Apr 1, 2026", "instructor": "Doug Rehnstrom", "title": "CDL", "attendees": 100},
        {"date": "Apr 2, 2026", "instructor": "Doug Rehnstrom", "title": "Advanced CDL", "attendees": 100}
    ]
}

generate_trip_infographic(example_data)