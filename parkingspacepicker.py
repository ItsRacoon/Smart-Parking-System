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

try:
    with open('CarParkPos', 'rb') as f:
        posList = pickle.load(f)
except:
    posList = []

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
        "- Left click and drag: Draw new parking space",
        "- Left click on space: Drag to move",
        "- Right click on space: Delete space",
        f"- Total spaces: {len(posList)}",
        "- Press 'r' to reset all spaces",
        "- Press 's' to save and exit",
        "- Press 'q' to quit without saving"
    ]
    
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

while True:
    # Create a copy of the original image to draw on
    img_copy = img.copy()
    
    # Draw all existing rectangles
    for i, pos in enumerate(posList):
        color = (255, 0, 255)  # Default color
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
        cv2.circle(img_copy, handle_pos, resize_handle_size // 2, (0, 255, 0), -1)
    
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
        with open('CarParkPos', 'wb') as f:
            pickle.dump(posList, f)
    elif key == ord('s'):
        with open('CarParkPos', 'wb') as f:
            pickle.dump(posList, f)
        break

cv2.destroyAllWindows()