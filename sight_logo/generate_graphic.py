import os
import sys
import io
from google.cloud import storage
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
    
    # --- Fetch & Draw Company Logo from GCS ---
    try:
        bucket_name = "roitraining-dashboard-grounding"
        blob_name = f"company_logos/{data['company']}.png"
        
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        logo_bytes = blob.download_as_bytes()
        company_logo = Image.open(io.BytesIO(logo_bytes))
        
        # Scale logo to approx 1/3 height of white header section (header_height - 50 = 200px)
        # 1/3 of header row (~80px height)
        max_logo_h = 70
        aspect_ratio = company_logo.width / company_logo.height
        new_w = int(max_logo_h * aspect_ratio)
        company_logo = company_logo.resize((new_w, max_logo_h), Image.Resampling.LANCZOS)
        
        # Paste logo left-aligned, below the title
        img.paste(company_logo, (50, 105), mask=company_logo if company_logo.mode == 'RGBA' else None)
        print(f"Successfully added logo: {blob_name}")
    except Exception as e:
        print(f"Warning: Could not fetch company logo from GCS ({e}). Using text fallback.")
        draw.text((50, 110), data["company"], fill=black, font=font_bold)

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

    # Cache for instructor photos to avoid redundant downloads
    instructor_cache = {}
    storage_client = storage.Client()

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
            instructor_name = entry['instructor']
            
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
            
            # --- Instructor Photo (Circle) ---
            circle_bbox = [x - 100, card_top + 60, x - 50, card_top + 110]
            # Draw gray placeholder circle first
            draw.ellipse(circle_bbox, fill="#CCCCCC")
            
            # Fetch and paste instructor photo
            try:
                if instructor_name not in instructor_cache:
                    blob_name = f"instructor_photos/{instructor_name}.jpg"
                    bucket = storage_client.bucket("roitraining-dashboard-grounding")
                    blob = bucket.blob(blob_name)
                    
                    photo_bytes = blob.download_as_bytes()
                    photo_img = Image.open(io.BytesIO(photo_bytes)).convert("RGBA")
                    
                    # Circular Crop
                    size = (100, 100)
                    photo_img = ImageOps.fit(photo_img, size, centering=(0.5, 0.5))
                    mask = Image.new('L', size, 0)
                    mask_draw = ImageDraw.Draw(mask)
                    mask_draw.ellipse((0, 0) + size, fill=255)
                    
                    circular_photo = Image.new('RGBA', size, (0, 0, 0, 0))
                    circular_photo.paste(photo_img, (0, 0), mask=mask)
                    
                    # Resize to fit the circle_bbox (50x50)
                    circular_photo = circular_photo.resize((50, 50), Image.Resampling.LANCZOS)
                    instructor_cache[instructor_name] = circular_photo
                    print(f"Successfully cached instructor: {instructor_name}")
                
                # Paste from cache
                img.paste(instructor_cache[instructor_name], (circle_bbox[0], circle_bbox[1]), 
                          mask=instructor_cache[instructor_name])
            except Exception as e:
                print(f"Warning: Could not fetch instructor photo for {instructor_name} ({e})")

            # Instructor Name (Split)
            name_parts = instructor_name.split(' ')
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
        {"date": "Apr 1, 2026", "instructor": "Steve Lockwood", "title": "CDL", "attendees": 100},
        {"date": "Apr 2, 2026", "instructor": "Doug Rehnstrom", "title": "Advanced CDL", "attendees": 100}
    ]
}

generate_trip_infographic(example_data)