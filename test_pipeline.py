import requests
from PIL import Image, ImageDraw, ImageFont
import io
import json

def create_test_image():
    # Create a white image
    img = Image.new('RGB', (800, 1000), color='white')
    d = ImageDraw.Draw(img)
    
    # Add some text that looks like a receipt
    text = """
    WALMART SUPERCENTER
    123 Main Street
    Anytown, USA
    
    Date: 2025-01-02
    Time: 14:30
    
    Item 1       $10.00
    Item 2       $20.00
    
    TOTAL        $30.00
    
    Thank you for shopping!
    """
    
    # Use default font
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 20)
    except:
        font = ImageFont.load_default()
        
    d.text((50, 50), text, fill='black', font=font)
    
    # Save to bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

def test_upload():
    url = "http://localhost:8000/upload"
    img_data = create_test_image()
    
    files = {'file': ('test_receipt.png', img_data, 'image/png')}
    
    try:
        print("Sending request to", url)
        response = requests.post(url, files=files)
        
        if response.status_code == 200:
            print("Success!")
            data = response.json()
            print(json.dumps(data, indent=2))
            
            # Basic assertions
            assert "document_type" in data
            assert "confidence_scores" in data
            assert "extracted_fields" in data
            print("\nTest Passed: Response structure is correct.")
        else:
            print(f"Failed with status code {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_upload()
