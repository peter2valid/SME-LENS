from PIL import Image, ImageDraw, ImageFont
import os

def create_receipt():
    # Create white image
    img = Image.new('RGB', (600, 400), color='white')
    d = ImageDraw.Draw(img)
    
    # Simple text (using default font since we might not have custom ones)
    d.text((20, 50), "Bold Theme Cafe", fill=(0,0,0))
    d.text((20, 100), "Date: 02/02/2026", fill=(0,0,0))
    d.text((20, 150), "Total: $123.45", fill=(0,0,0))
    
    img.save("bold_test_receipt.png")
    print("Created bold_test_receipt.png")

if __name__ == "__main__":
    create_receipt()
