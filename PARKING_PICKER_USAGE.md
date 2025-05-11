# Parking Space Picker Usage Guide

This tool allows you to define parking spaces in your parking lot image using both manual and automatic detection methods.

## Getting Started

1. Make sure you have an image of your parking lot named `carParkImg.png` in the same directory
2. Run the tool with `python parkingspacepicker.py`

## Features

### Manual Selection Mode

In manual mode, you can:
- **Draw new spaces**: Click and drag to create a new parking space
- **Move spaces**: Click on an existing space and drag to move it
- **Delete spaces**: Right-click on a space to delete it
- **Reset all spaces**: Press 'r' to clear all spaces

### Automatic Detection Mode

In automatic mode, the system will:
- Analyze the image to detect potential parking spaces
- Show you the detected spaces for confirmation
- Allow you to adjust the results before confirming

To use automatic detection:
1. Press 'a' to start the detection process
2. Wait for the system to analyze the image
3. Review the detected spaces
4. Use the following options:
   - Press 'y' to confirm and use the detected spaces
   - Press 'n' to cancel and return to the previous spaces
   - Press '+' to add more spaces using a grid pattern
   - Press '-' to reduce spaces by removing outliers

### Switching Between Modes

- Press 'a' to run automatic detection
- Press 'm' to switch to manual mode
- The current mode is displayed in the UI

### Saving Your Work

- Press 's' to save the current spaces and exit
- Press 'q' to quit without saving changes

## Color Coding

The application uses different colors to indicate the status of parking spaces:

- **Purple (255, 0, 255)**: Regular parking space in manual mode
- **Yellow (0, 255, 255)**: Currently selected parking space
- **Green (0, 255, 0)**: 
  - Newly created space
  - Available space in automatic detection preview
  - Resize handle at the corner of a space
- **Red (0, 0, 255)**: Occupied parking space (when used with detection system)
- **Orange (255, 165, 0)**: Booked but empty parking space (when used with booking system)

During automatic detection confirmation:
- **Green (0, 255, 0)**: Automatically detected parking spaces
- **White Text with Black Border**: Instructions and information

## Tips for Best Results

### For Automatic Detection:
- Use a clear image with good lighting
- Ensure parking spaces have visible markings
- The image should have good contrast between spaces and surroundings

### For Manual Selection:
- Zoom in on the image if needed for precision
- Use consistent spacing between parking spaces
- Start from one corner and work systematically

## Troubleshooting

If automatic detection doesn't work well:
1. Try manual mode instead
2. Improve the image quality or lighting
3. Adjust the image contrast before running the tool
4. Use the '+' and '-' options during confirmation to refine results

Remember that you can always manually adjust the automatically detected spaces after confirmation.