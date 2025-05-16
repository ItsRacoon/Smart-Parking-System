import os
import sys

def check_files():
    """Check if critical files exist and print status"""
    critical_files = [
        'carParkPos',
        'carPark.mp4',
        'auth.py',
        'app.py'
    ]
    
    missing_files = []
    
    for file in critical_files:
        if not os.path.exists(file):
            missing_files.append(file)
            print(f"ERROR: Missing critical file: {file}")
        else:
            print(f"OK: Found file: {file}")
    
    if missing_files:
        print("\nWARNING: Some critical files are missing!")
        print("Please ensure all files are uploaded to the server.")
        return False
    else:
        print("\nAll critical files are present.")
        return True

if __name__ == "__main__":
    print("Checking for critical files...")
    check_files()