import qrcode
from PIL import Image
from io import BytesIO
import base64
import os

def generate_test_qr():
    try:
        # Create QR code
        img = qrcode.make("TEST-QR-CODE-123")
        
        # Save to file for direct inspection
        img.save("test_qr.png")
        print(f"QR code saved to {os.path.abspath('test_qr.png')}")
        
        # Also test base64 encoding
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        # Encode as base64 string
        qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        print(f"Base64 QR code length: {len(qr_base64)}")
        
        # Save a sample HTML file with the embedded QR code
        with open("test_qr.html", "w") as f:
            f.write(f"""
            <html>
            <body>
                <h1>QR Code Test</h1>
                <img src="data:image/png;base64,{qr_base64}" width="200" height="200">
            </body>
            </html>
            """)
        print(f"Test HTML saved to {os.path.abspath('test_qr.html')}")
        
        return True
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing QR code generation...")
    result = generate_test_qr()
    print(f"Test {'succeeded' if result else 'failed'}")