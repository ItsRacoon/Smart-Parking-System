import cv2
import pickle
import numpy as np

# Default rectangle size
default_width, default_height = 107, 48

# Global variables for drag functionality
drawing = False
start_point = (-1, -1)
end_point = (-1, -1)
current_rect = None
dragging = False
drag_start_pos = None
resize_mode = False
selected_rect_index = -1
resize_handle_size = 10
detection_mode = "manual"  # Can be "manual" or "auto"

try:
    with open('CarParkPos', 'rb') as f:
        posList = pickle.load(f)
except:
    posList = []

def auto_detect_parking_spaces(image):
    """
    Automatically detect potential parking spaces in the image
    using computer vision techniques
    """
    # Try multiple detection methods and combine results
    methods = [
        contour_based_detection,
        grid_based_detection,
        line_based_detection
    ]
    
    all_spaces = []
    for method in methods:
        try:
            spaces = method(image)
            print(f"Method {method.__name__} found {len(spaces)} spaces")
            all_spaces.extend(spaces)
        except Exception as e:
            print(f"Error in {method.__name__}: {str(e)}")
    
    # Remove duplicates (spaces that are too close to each other)
    filtered_spaces = []
    for space in all_spaces:
        # Check if this space is too close to any already filtered space
        is_duplicate = False
        for filtered_space in filtered_spaces:
            distance = np.sqrt((space[0] - filtered_space[0])**2 + (space[1] - filtered_space[1])**2)
            if distance < default_width / 2:  # If centers are closer than half width
                is_duplicate = True
                break
        
        if not is_duplicate:
            filtered_spaces.append(space)
    
    print(f"After filtering duplicates: {len(filtered_spaces)} spaces")
    
    # If we still don't have enough spaces, fall back to a simple grid
    if len(filtered_spaces) < 5:
        print("All methods found too few spaces, using simple grid fallback")
        filtered_spaces = simple_grid_fallback(image)
    
    return filtered_spaces

def contour_based_detection(image):
    """
    Detect parking spaces using contour detection
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to reduce noise
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Apply edge detection
    edges = cv2.Canny(blur, 50, 150)
    
    # Dilate the edges to connect nearby edges
    kernel = np.ones((3, 3), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=2)
    
    # Find contours
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter contours by size and shape
    min_area = 1000  # Minimum area for a parking space
    max_area = 10000  # Maximum area for a parking space
    aspect_ratio_range = (1.5, 3.0)  # Expected aspect ratio range for parking spaces
    
    detected_spaces = []
    
    for contour in contours:
        area = cv2.contourArea(contour)
        if min_area < area < max_area:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = float(w) / h if h > 0 else 0
            
            if aspect_ratio_range[0] < aspect_ratio < aspect_ratio_range[1]:
                # Adjust to standard size
                detected_spaces.append((x, y))
    
    return detected_spaces

def grid_based_detection(image):
    """
    Detect parking spaces using a grid-based approach with image analysis
    """
    height, width = image.shape[:2]
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Define grid parameters
    rows = 4  # Number of rows in the grid
    cols = 6  # Number of columns in the grid
    
    # Calculate cell dimensions
    cell_width = width // cols
    cell_height = height // rows
    
    # Create grid of parking spaces
    spaces = []
    
    for row in range(rows):
        for col in range(cols):
            x = col * cell_width + cell_width // 4  # Add offset to center in cell
            y = row * cell_height + cell_height // 4
            
            # Get the cell region
            cell_roi = gray[y:y+cell_height//2, x:x+cell_width//2]
            
            # Skip if cell is empty
            if cell_roi.size == 0:
                continue
                
            # Calculate variance in the cell (high variance might indicate a parking space boundary)
            variance = np.var(cell_roi)
            
            # Skip cells with very low variance (likely empty areas)
            if variance < 100:  # Threshold may need adjustment
                continue
                
            spaces.append((x, y))
    
    return spaces

def line_based_detection(image):
    """
    Detect parking spaces using line detection
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Apply Canny edge detection
    edges = cv2.Canny(blur, 50, 150)
    
    # Detect lines using Hough Line Transform
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=100, maxLineGap=10)
    
    if lines is None:
        return []
    
    # Group lines by orientation (horizontal vs vertical)
    horizontal_lines = []
    vertical_lines = []
    
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if abs(x2 - x1) > abs(y2 - y1):  # Horizontal line
            horizontal_lines.append((x1, y1, x2, y2))
        else:  # Vertical line
            vertical_lines.append((x1, y1, x2, y2))
    
    # Find intersections of horizontal and vertical lines
    intersections = []
    for h_line in horizontal_lines:
        for v_line in vertical_lines:
            # Simple intersection check
            h_x1, h_y1, h_x2, h_y2 = h_line
            v_x1, v_y1, v_x2, v_y2 = v_line
            
            # Skip if lines are far apart
            if min(h_x1, h_x2) > max(v_x1, v_x2) or max(h_x1, h_x2) < min(v_x1, v_x2):
                continue
            if min(h_y1, h_y2) > max(v_y1, v_y2) or max(h_y1, h_y2) < min(v_y1, v_y2):
                continue
            
            # Approximate intersection point
            x = (min(h_x1, h_x2) + max(v_x1, v_x2)) // 2
            y = (min(v_y1, v_y2) + max(h_y1, h_y2)) // 2
            
            intersections.append((x, y))
    
    return intersections

def simple_grid_fallback(image):
    """
    Create a simple grid of parking spaces as a last resort
    """
    height, width = image.shape[:2]
    
    # Define grid parameters based on default space size
    rows = height // (default_height + 10)
    cols = width // (default_width + 10)
    
    # Ensure reasonable grid size
    rows = max(2, min(rows, 8))
    cols = max(3, min(cols, 10))
    
    # Calculate spacing
    row_spacing = height // rows
    col_spacing = width // cols
    
    # Create grid
    spaces = []
    for row in range(rows):
        for col in range(cols):
            x = col * col_spacing + 10
            y = row * row_spacing + 10
            spaces.append((x, y))
    
    return spaces

def is_near_point(p1, p2, threshold=10):
    """Check if two points are near each other"""
    return abs(p1[0] - p2[0]) < threshold and abs(p1[1] - p2[1]) < threshold

def is_in_rect(point, rect_pos):
    """Check if a point is inside a rectangle"""
    x, y = point
    rx, ry = rect_pos
    return rx <= x <= rx + default_width and ry <= y <= ry + default_height

def is_near_resize_handle(point, rect_pos):
    """Check if a point is near the resize handle (bottom-right corner)"""
    x, y = point
    rx, ry = rect_pos
    handle_x, handle_y = rx + default_width, ry + default_height
    return is_near_point((x, y), (handle_x, handle_y), resize_handle_size)

def mouseClick(events, x, y, flags, params):
    global drawing, start_point, end_point, current_rect, dragging, drag_start_pos, resize_mode, selected_rect_index
    
    # Left button down - start drawing or select for dragging
    if events == cv2.EVENT_LBUTTONDOWN:
        # Check if clicking on an existing rectangle for dragging
        for i, pos in enumerate(posList):
            if is_in_rect((x, y), pos):
                dragging = True
                selected_rect_index = i
                drag_start_pos = (x, y)
                break
            elif is_near_resize_handle((x, y), pos):
                resize_mode = True
                selected_rect_index = i
                drag_start_pos = (x, y)
                break
        else:  # Not on any existing rectangle, start drawing a new one
            drawing = True
            start_point = (x, y)
            end_point = (x, y)
    
    # Mouse move - update drawing or dragging
    elif events == cv2.EVENT_MOUSEMOVE:
        if drawing:
            end_point = (x, y)
        elif dragging and selected_rect_index != -1:
            # Calculate the movement delta
            dx = x - drag_start_pos[0]
            dy = y - drag_start_pos[1]
            # Update the position
            old_pos = posList[selected_rect_index]
            posList[selected_rect_index] = (old_pos[0] + dx, old_pos[1] + dy)
            # Update drag start position
            drag_start_pos = (x, y)
        elif resize_mode and selected_rect_index != -1:
            # We're not actually changing the width/height globally, just for this specific rectangle
            # This would require modifying the data structure to store width/height per rectangle
            # For simplicity, we'll just update the position to simulate resizing
            pass  # Placeholder for actual resize implementation
    
    # Left button up - finish drawing or dragging
    elif events == cv2.EVENT_LBUTTONUP:
        if drawing:
            drawing = False
            # Calculate the top-left corner and dimensions
            x1, y1 = min(start_point[0], end_point[0]), min(start_point[1], end_point[1])
            # Add the new rectangle
            posList.append((x1, y1))
            start_point = (-1, -1)
            end_point = (-1, -1)
        elif dragging:
            dragging = False
            selected_rect_index = -1
        elif resize_mode:
            resize_mode = False
            selected_rect_index = -1
    
    # Right button down - delete rectangle
    elif events == cv2.EVENT_RBUTTONDOWN:
        for i, pos in enumerate(posList):
            if is_in_rect((x, y), pos):
                posList.pop(i)
                break
    
    # Save the updated positions
    with open('CarParkPos', 'wb') as f:
        pickle.dump(posList, f)

def draw_ui_elements(img):
    """Draw UI elements like instructions and controls"""
    instructions = [
        "Controls:",
        "- Left click and drag: Draw new parking space (Manual mode)",
        "- Left click on space: Drag to move",
        "- Right click on space: Delete space",
        f"- Total spaces: {len(posList)}",
        "- Press 'r' to reset all spaces",
        "- Press 'a' to auto-detect parking spaces",
        "- Press 'm' to switch to manual mode",
        "- Press 's' to save and exit",
        "- Press 'q' to quit without saving",
        f"- Current mode: {detection_mode.upper()}"
    ]
    
    # Add mode-specific instructions
    if detection_mode == "auto":
        instructions.append("Auto mode: Spaces were detected automatically")
        instructions.append("You can still manually add/move/delete spaces")
    else:
        instructions.append("Manual mode: Draw spaces by clicking and dragging")
    
    y_offset = 30
    for i, text in enumerate(instructions):
        cv2.putText(img, text, (10, y_offset + i * 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        cv2.putText(img, text, (10, y_offset + i * 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)

# Main loop
img = cv2.imread('carParkImg.png')
if img is None:
    print("Error: Could not load image 'carParkImg.png'. Please make sure the file exists.")
    exit()

window_name = "Parking Space Picker"
cv2.namedWindow(window_name)
cv2.setMouseCallback(window_name, mouseClick)

def run_auto_detection():
    """Run automatic detection and update posList"""
    global posList, detection_mode
    
    # Show processing message
    processing_img = img.copy()
    # White text with black border
    cv2.putText(processing_img, "Processing... Please wait", (50, 50), 
               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)  # Black border
    cv2.putText(processing_img, "Processing... Please wait", (50, 50), 
               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 1)  # White text
    cv2.imshow(window_name, processing_img)
    cv2.waitKey(1)
    
    # Run detection
    detected_spaces = auto_detect_parking_spaces(img)
    
    # Confirm with user
    confirm_img = img.copy()
    for i, pos in enumerate(detected_spaces):
        # Green for automatically detected spaces
        cv2.rectangle(confirm_img, pos, (pos[0] + default_width, pos[1] + default_height), (0, 255, 0), 2)
        cv2.putText(confirm_img, f"P{i+1:03d}", (pos[0] + 5, pos[1] + 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # Draw instructions
    instructions = [
        f"Detected {len(detected_spaces)} parking spaces",
        "Press 'y' to confirm",
        "Press 'n' to cancel",
        "Press '+' to add more spaces (grid)",
        "Press '-' to reduce spaces (remove outliers)"
    ]
    
    for i, text in enumerate(instructions):
        y_pos = 30 + i * 30
        # White text with black border for instructions
        cv2.putText(confirm_img, text, (10, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)  # Black border
        cv2.putText(confirm_img, text, (10, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)  # White text
    
    cv2.imshow(window_name, confirm_img)
    
    # Wait for confirmation
    while True:
        key = cv2.waitKey(0) & 0xFF
        if key == ord('y'):
            posList = detected_spaces
            detection_mode = "auto"
            print(f"Auto-detection confirmed: {len(posList)} spaces")
            break
        elif key == ord('n'):
            print("Auto-detection cancelled")
            break
        elif key == ord('+'):
            # Add more spaces using grid
            height, width = img.shape[:2]
            grid_spaces = simple_grid_fallback(img)
            
            # Add grid spaces that don't overlap with existing ones
            for grid_pos in grid_spaces:
                is_duplicate = False
                for pos in detected_spaces:
                    distance = np.sqrt((grid_pos[0] - pos[0])**2 + (grid_pos[1] - pos[1])**2)
                    if distance < default_width / 2:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    detected_spaces.append(grid_pos)
            
            # Update the confirmation image
            confirm_img = img.copy()
            for i, pos in enumerate(detected_spaces):
                # Green for automatically detected spaces
                cv2.rectangle(confirm_img, pos, (pos[0] + default_width, pos[1] + default_height), (0, 255, 0), 2)
                cv2.putText(confirm_img, f"P{i+1:03d}", (pos[0] + 5, pos[1] + 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            for i, text in enumerate(instructions):
                if i == 0:
                    text = f"Detected {len(detected_spaces)} parking spaces"
                y_pos = 30 + i * 30
                # White text with black border for instructions
                cv2.putText(confirm_img, text, (10, y_pos), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)  # Black border
                cv2.putText(confirm_img, text, (10, y_pos), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)  # White text
            
            cv2.imshow(window_name, confirm_img)
            
        elif key == ord('-'):
            # Remove outliers (spaces that are far from the majority)
            if len(detected_spaces) > 5:
                # Calculate center of mass of all spaces
                center_x = sum(pos[0] for pos in detected_spaces) / len(detected_spaces)
                center_y = sum(pos[1] for pos in detected_spaces) / len(detected_spaces)
                
                # Calculate distances from center
                distances = []
                for pos in detected_spaces:
                    distance = np.sqrt((pos[0] - center_x)**2 + (pos[1] - center_y)**2)
                    distances.append((distance, pos))
                
                # Sort by distance
                distances.sort(key=lambda x: x[0])
                
                # Keep only the closest 80%
                keep_count = int(len(detected_spaces) * 0.8)
                detected_spaces = [pos for _, pos in distances[:keep_count]]
                
                # Update the confirmation image
                confirm_img = img.copy()
                for i, pos in enumerate(detected_spaces):
                    # Green for automatically detected spaces
                    cv2.rectangle(confirm_img, pos, (pos[0] + default_width, pos[1] + default_height), (0, 255, 0), 2)
                    cv2.putText(confirm_img, f"P{i+1:03d}", (pos[0] + 5, pos[1] + 20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                for i, text in enumerate(instructions):
                    if i == 0:
                        text = f"Detected {len(detected_spaces)} parking spaces"
                    y_pos = 30 + i * 30
                    # White text with black border for instructions
                    cv2.putText(confirm_img, text, (10, y_pos), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)  # Black border
                    cv2.putText(confirm_img, text, (10, y_pos), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)  # White text
                
                cv2.imshow(window_name, confirm_img)
    
    # Save the updated positions
    with open('CarParkPos', 'wb') as f:
        pickle.dump(posList, f)

while True:
    # Create a copy of the original image to draw on
    img_copy = img.copy()
    
    # Draw all existing rectangles
    for i, pos in enumerate(posList):
        color = (255, 0, 255)  # Default color (Purple)
        thickness = 2
        
        # Highlight selected rectangle
        if i == selected_rect_index:
            color = (0, 255, 255)  # Yellow for selected
            thickness = 3
            
        # Draw the rectangle
        cv2.rectangle(img_copy, pos, (pos[0] + default_width, pos[1] + default_height), color, thickness)
        
        # Draw space ID
        cv2.putText(img_copy, f"P{i+1:03d}", (pos[0] + 5, pos[1] + 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Draw resize handle at bottom-right corner
        handle_pos = (pos[0] + default_width, pos[1] + default_height)
        cv2.circle(img_copy, handle_pos, resize_handle_size // 2, (0, 255, 0), -1)  # Green resize handle
    
    # Draw the rectangle being created
    if drawing and start_point != (-1, -1) and end_point != (-1, -1):
        x1, y1 = min(start_point[0], end_point[0]), min(start_point[1], end_point[1])
        x2, y2 = max(start_point[0], end_point[0]), max(start_point[1], end_point[1])
        cv2.rectangle(img_copy, (x1, y1), (x2, y2), (0, 255, 0), 2)
    
    # Draw UI elements
    draw_ui_elements(img_copy)
    
    # Show the image
    cv2.imshow(window_name, img_copy)
    
    # Handle keyboard input
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('r'):
        posList = []
        detection_mode = "manual"
        with open('CarParkPos', 'wb') as f:
            pickle.dump(posList, f)
    elif key == ord('a'):
        # Run automatic detection
        run_auto_detection()
    elif key == ord('m'):
        # Switch to manual mode
        detection_mode = "manual"
    elif key == ord('s'):
        with open('CarParkPos', 'wb') as f:
            pickle.dump(posList, f)
        break

cv2.destroyAllWindows()