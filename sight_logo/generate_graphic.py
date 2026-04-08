import os
import sys
import io
import datetime
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
    
    # Calculate rows based on custom mapping for 1-15 items
    layout_map = {
        1: [1], 2: [2], 3: [3], 4: [4], 5: [5],
        6: [3, 3], 7: [4, 3], 8: [4, 4], 9: [5, 4], 10: [5, 5],
        11: [4, 4, 3], 12: [4, 4, 4], 13: [5, 4, 4], 14: [5, 5, 4], 15: [5, 5, 5]
    }
    
    distribution = layout_map.get(num_classes, [5] * (num_classes // 5) + ([num_classes % 5] if num_classes % 5 else []))
    max_across = max(distribution) if distribution else 0
    center_layout = max_across < 5
    
    rows = []
    current_idx = 0
    for count in distribution:
        rows.append(classes[current_idx : current_idx + count])
        current_idx += count
    
    total_height = header_height + (len(rows) * row_height) + 100
    img = Image.new('RGB', (width, total_height), color=white)
    draw = ImageDraw.Draw(img)

    # Load Fonts (Assumes standard paths, adjust for your OS)
    # try:
    #     font_bold = ImageFont.truetype("arialbd.ttf", 28)
    #     font_reg = ImageFont.truetype("arial.ttf", 20)
    #     font_large = ImageFont.truetype("arialbd.ttf", 87)
    # except:
    #     font_bold = font_reg = font_large = ImageFont.load_default()

    font_path = "Inter.ttf"
    font_bold_path = "Inter_24pt-Bold.ttf"
    try:
        # Checking if the file exists to provide a helpful error if it doesn't
        if not os.path.exists(font_path):
            raise FileNotFoundError(f"Font file not found at {font_path}")

        # Applying Inter.ttf to your various font sizes
        font_bold = ImageFont.truetype(font_bold_path, 24)

        font_reg = ImageFont.truetype(font_path, 15)
        font_large = ImageFont.truetype(font_path, 40)
        
        # If you want a specific "Bold" version of Inter, 
        # you would typically load Inter-Bold.ttf here.
        # Otherwise, PIL will use the standard Inter.ttf for all.
        
    except Exception as e:
        print(f"Warning: Could not load Inter.ttf ({e}). Falling back to default.")
        font_bold = font_reg = font_large = ImageFont.load_default()


    storage_client = None
    try:
        storage_client = storage.Client()
    except Exception as e:
        print(f"Warning: Could not initialize storage client ({e})")

    # --- 1. Header Construction ---
    # Fetch & Draw Google Cloud Logo from GCS
    try:
        if not storage_client:
            raise Exception("Storage client not initialized")
        bucket = storage_client.bucket("roitraining-dashboard-grounding")
        gc_logo_blob = bucket.blob("company_logos/Google Cloud.png")
        gc_logo_bytes = gc_logo_blob.download_as_bytes()
        gc_logo = Image.open(io.BytesIO(gc_logo_bytes))
        attendee_logo = None
        try:
            attendee_logo_blob = bucket.blob("company_logos/attendee icon.png") # Adjust path as needed
            attendee_bytes = attendee_logo_blob.download_as_bytes()
            attendee_logo = Image.open(io.BytesIO(attendee_bytes)).convert("RGBA")
            
            # Scale to fit nicely (e.g., 27px height - 40% smaller than previous 45px)
            icon_h = 27
            aspect = attendee_logo.width / attendee_logo.height
            attendee_logo = attendee_logo.resize((int(icon_h * aspect), icon_h), Image.Resampling.LANCZOS)
        except Exception as e:
            print(f"Warning: Could not fetch attendee logo ({e})")


        # Trim whitespace from Google Cloud logo
        if gc_logo.mode != 'RGBA':
            gc_logo = gc_logo.convert('RGBA')
        bbox = gc_logo.getbbox()
        if bbox:
            gc_logo = gc_logo.crop(bbox)
            
        # Scale Google Cloud logo (making it bigger)
        gc_logo_h = 80
        aspect = gc_logo.width / gc_logo.height
        gc_logo = gc_logo.resize((int(gc_logo_h * aspect), gc_logo_h), Image.Resampling.LANCZOS)
        
        img.paste(gc_logo, (50, 42), mask=gc_logo if gc_logo.mode == 'RGBA' else None)
        title_x = 50 + int(gc_logo_h * aspect) + 15
    except Exception as e:
        print(f"Warning: Could not fetch Google Cloud logo ({e})")
        title_x = 50

    # Draw "TRIP Report" title
    # draw.text((title_x, 40), "TRIP Report", fill=black, font=font_large)
    
    # --- Fetch & Draw Company Logo from GCS ---
    try:
        if not storage_client:
            raise Exception("Storage client not initialized")
        bucket_name = "roitraining-dashboard-grounding"
        blob_name = f"company_logos/{data['company']}.png"
        
        # storage_client already initialized above
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        logo_bytes = blob.download_as_bytes()
        company_logo = Image.open(io.BytesIO(logo_bytes))
        
        # Trim whitespace from company logo
        if company_logo.mode != 'RGBA':
            company_logo = company_logo.convert('RGBA')
        bbox = company_logo.getbbox()
        if bbox:
            company_logo = company_logo.crop(bbox)
            
        # Scale logo to be 20% smaller than previous 70px (70 * 0.8 = 56)
        max_logo_h = 56
        aspect_ratio = company_logo.width / company_logo.height
        new_w = int(max_logo_h * aspect_ratio)
        company_logo = company_logo.resize((new_w, max_logo_h), Image.Resampling.LANCZOS)
        
        # Paste logo moved 50px to the right (from x=50 to x=100)
        company_logo_y = 122 + 10
        img.paste(company_logo, (100, company_logo_y), mask=company_logo if company_logo.mode == 'RGBA' else None)
        print(f"Successfully added logo: {blob_name}")
    except Exception as e:
        print(f"Warning: Could not fetch company logo from GCS ({e}). Using text fallback.")
        draw.text((100, 132), data["company"], fill=black, font=font_bold)

    # --- 2. Dark Blue Section ---
    draw.rectangle([0, header_height - 50, width, total_height], fill=bg_color)
    
    title_text = "Completed PLLJ Training Overview"
    company_text = data["company"]
    
    if center_layout:
        bbox_title = draw.textbbox((0, 0), title_text, font=font_bold)
        title_w = bbox_title[2] - bbox_title[0]
        draw.text(((width - title_w) // 2, header_height - 30), title_text, fill=white, font=font_bold)
        
        bbox_company = draw.textbbox((0, 0), company_text.upper(), font=font_bold)
        company_w = bbox_company[2] - bbox_company[0]
        draw.text(((width - company_w) // 2, header_height + 14), company_text.upper(), fill=bright_blue, font=font_bold)
    else:
        draw.text((50, header_height - 30), title_text, fill=white, font=font_large)
        draw.text((50, header_height + 14), company_text.upper(), fill=bright_blue, font=font_bold)

    # --- 3. Timeline Rows ---
    current_y = header_height + 150
    margin = 50
    items_per_row = 5
    min_gap = 20
    
    # Calculate card width dynamically based on items per row and minimum gap
    content_width = width - (2 * margin)
    card_w = (content_width - (items_per_row - 1) * min_gap) / items_per_row
    
    # Calculate fixed step and padding based on the dynamic card width
    padding = margin + (card_w / 2)
    fixed_step = card_w + min_gap

    # Cache for instructor photos to avoid redundant downloads
    instructor_cache = {}

    for row in rows:
        num_in_row = len(row)
        
        # Calculate x-positions
        if center_layout:
            row_width = (num_in_row - 1) * fixed_step + card_w
            row_start_x = (width - row_width) / 2
            x_positions = [int(row_start_x + card_w/2 + (i * fixed_step)) for i in range(num_in_row)]
        else:
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
            
            # --- Vertical connector ---
            # We define the bar height clearly to use as anchor points
            bar_half_length = 40
            line_top = current_y - bar_half_length
            line_bottom = current_y + bar_half_length
            
            draw.line([(x, line_top), (x, line_bottom)], fill=bright_blue, width=3)


            # --- Date Pill (Moved Up) ---
            # Pill height is 50, so its bottom (y2) should be line_top
            pill_w, pill_h = 140, 50
            pill_top = line_top - pill_h
            draw.rounded_rectangle([x - pill_w//2, pill_top, x + pill_w//2, line_top], 
                                   radius=20, fill="#345491")
            
            # Centering text inside the moved pill
            draw.text((x - 45, pill_top + 15), entry['date'], fill=white, font=font_reg)


            # --- Course Card (Below) ---
            card_h = 180
            card_top = current_y + 40
            draw.rounded_rectangle([x - card_w//2, card_top, x + card_w//2, card_top + card_h], 
                                   radius=15, fill="#2A4A8E")
            
            # Course Title (wrapped, max 3 lines)
            title = entry['title']
            max_title_w = card_w - 20
            words = title.split()
            title_lines = []
            while words and len(title_lines) < 3:
                line = ""
                while words and draw.textbbox((0, 0), line + words[0], font=font_reg)[2] < max_title_w:
                    line += (words.pop(0) + " ")
                if not line: line = words.pop(0)
                title_lines.append(line.strip())
            
            if words: # If there's still more text after 3 lines
                title_lines[-1] = title_lines[-1][:max(0, len(title_lines[-1])-3)] + "..."
            
            for j, line in enumerate(title_lines):
                draw.text((x - card_w//2 + 10, card_top + 10 + (j * 20)), line, fill=white, font=font_reg)
            
            # --- Instructor Photo (Circle) ---
            # Position photo in lower left with a fixed margin
            photo_size = 50
            photo_x = x - card_w//2 + 10
            photo_y = card_top + card_h - photo_size - 10
            circle_bbox = [photo_x, photo_y, photo_x + photo_size, photo_y + photo_size]
            
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
                    crop_res = 100
                    photo_img = ImageOps.fit(photo_img, (crop_res, crop_res), centering=(0.5, 0.5))
                    mask = Image.new('L', (crop_res, crop_res), 0)
                    mask_draw = ImageDraw.Draw(mask)
                    mask_draw.ellipse((0, 0, crop_res, crop_res), fill=255)
                    
                    circular_photo = Image.new('RGBA', (crop_res, crop_res), (0, 0, 0, 0))
                    circular_photo.paste(photo_img, (0, 0), mask=mask)
                    
                    # Resize to fit the circle_bbox (50x50)
                    circular_photo = circular_photo.resize((photo_size, photo_size), Image.Resampling.LANCZOS)
                    instructor_cache[instructor_name] = circular_photo
                    print(f"Successfully cached instructor: {instructor_name}")
                
                # Paste from cache
                img.paste(instructor_cache[instructor_name], (int(circle_bbox[0]), int(circle_bbox[1])), 
                          mask=instructor_cache[instructor_name])
            except Exception as e:
                print(f"Warning: Could not fetch instructor photo for {instructor_name} ({e})")

            # Instructor Name (Split) - Positioned next to photo in lower left
            name_x = photo_x + photo_size + 10
            name_parts = instructor_name.split(' ')
            draw.text((name_x, photo_y + 5), name_parts[0], fill=white, font=font_reg)
            draw.text((name_x, photo_y + 25), name_parts[1], fill=white, font=font_reg)

            # --- Attendees (Stacked in Bottom Right of card) ---
            right_margin = 15
            attendee_text = str(entry['attendees'])
            
            if attendee_logo:
                # Calculate text width for centering
                bbox = draw.textbbox((0, 0), attendee_text, font=font_reg)
                text_width = bbox[2] - bbox[0]

                # Position text aligned with instructor's last name (photo_y + 25)
                text_y = int(photo_y + 25)
                
                # Position icon above the text, right-aligned to card margin
                icon_x = int(x + card_w/2 - attendee_logo.width - right_margin)
                icon_y = int(text_y - attendee_logo.height - 8)
                
                # Calculate centered text position relative to icon
                icon_center_x = icon_x + (attendee_logo.width // 2)
                text_x = int(icon_center_x - (text_width // 2))
                
                # Paste the image icon and draw text
                img.paste(attendee_logo, (icon_x, icon_y), mask=attendee_logo)
                draw.text((text_x, text_y), attendee_text, fill=white, font=font_reg)
            else:
                # Fallback to emoji if image fails to load
                emoji_text = f"👤 {attendee_text}"
                bbox = draw.textbbox((0, 0), emoji_text, font=font_reg)
                emoji_width = bbox[2] - bbox[0]
                icon_x = int(x + card_w/2 - emoji_width - right_margin)
                footer_y_fallback = card_top + card_h - 35
                draw.text((icon_x, footer_y_fallback), emoji_text, fill=white, font=font_reg)

            # --- Timeline Connector Dots (Drawn on top to ensure circles) ---
            dot_radius = 6
            draw.ellipse([x - dot_radius, line_top - dot_radius, x + dot_radius, line_top + dot_radius], fill=bright_blue)
            draw.ellipse([x - dot_radius, line_bottom - dot_radius, x + dot_radius, line_bottom + dot_radius], fill=bright_blue)

        current_y += row_height

    # --- 4. Footer ---
    try:
        # Fetch & Draw ROI Logo
        # storage_client already initialized
        roi_logo_blob = bucket.blob("company_logos/ROI.png")
        roi_logo_bytes = roi_logo_blob.download_as_bytes()
        roi_logo = Image.open(io.BytesIO(roi_logo_bytes))
        
        # Trim & Scale
        if roi_logo.mode != 'RGBA':
            roi_logo = roi_logo.convert('RGBA')
        roi_bbox = roi_logo.getbbox()
        if roi_bbox:
            roi_logo = roi_logo.crop(roi_bbox)
        
        roi_h = 40
        aspect = roi_logo.width / roi_logo.height
        roi_logo = roi_logo.resize((int(roi_h * aspect), roi_h), Image.Resampling.LANCZOS)
        
        img.paste(roi_logo, (50, total_height - 65), mask=roi_logo if roi_logo.mode == 'RGBA' else None)
    except Exception as e:
        print(f"Warning: Could not fetch ROI logo for footer ({e})")
        draw.text((50, total_height - 60), "🌐 ROI Training", fill=white, font=font_reg)

    # Save Output
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"trip_infographic_{timestamp}.png"
    img.save(output_path)
    print(f"Infographic generated: {output_path}")

# --- Example Usage ---
example_data = {
    "company": "Rackspace",
    "classes": [
        {"date": "Jan 1, 2026", "instructor": "Joey Gagliardo", "title": "Advanced Generative AI and Large Language Model Development Workshop for Enterprise Applications and Business Transformation", "attendees": 15},
        {"date": "Feb 1, 2026", "instructor": "Joey Gagliardo", "title": "Google ADK Supercalifragilistic Expialidocious", "attendees": 20},
        {"date": "Mar 1, 2026", "instructor": "Doug Rehnstrom", "title": "Gemini Workspace", "attendees": 9},
        {"date": "Apr 1, 2026", "instructor": "Steve Lockwood", "title": "CDL", "attendees": 100},
        {"date": "Apr 2, 2026", "instructor": "Doug Rehnstrom", "title": "Advanced CDL", "attendees": 100},
        {"date": "Apr 3, 2026", "instructor": "Doug Rehnstrom", "title": "Special Topics", "attendees": 100},
        {"date": "Jan 1, 2026", "instructor": "Joey Gagliardo", "title": "App Dev with LLM", "attendees": 15},
        {"date": "Feb 1, 2026", "instructor": "Joey Gagliardo", "title": "Google ADK", "attendees": 20},
        {"date": "Mar 1, 2026", "instructor": "Doug Rehnstrom", "title": "Gemini Workspace", "attendees": 9},
        {"date": "Apr 1, 2026", "instructor": "Steve Lockwood", "title": "CDL", "attendees": 100},
        {"date": "Apr 2, 2026", "instructor": "Doug Rehnstrom", "title": "Advanced CDL", "attendees": 100},
        {"date": "Apr 3, 2026", "instructor": "Doug Rehnstrom", "title": "Special Topics", "attendees": 100},
        {"date": "Jan 2, 2026", "instructor": "Joey Gagliardo", "title": "App Dev with LLM", "attendees": 15},
        {"date": "Feb 2, 2026", "instructor": "Joey Gagliardo", "title": "Google ADK", "attendees": 20},
        {"date": "Mar 2, 2026", "instructor": "Doug Rehnstrom", "title": "Gemini Workspace", "attendees": 9},
        {"date": "Apr 2, 2026", "instructor": "Steve Lockwood", "title": "CDL", "attendees": 100},
        {"date": "Apr 2, 2026", "instructor": "Doug Rehnstrom", "title": "Advanced CDL", "attendees": 100},
        {"date": "Apr 3, 2026", "instructor": "Doug Rehnstrom", "title": "Special Topics", "attendees": 100}
    ][0:9]
}

generate_trip_infographic(example_data)