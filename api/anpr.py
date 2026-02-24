from dotenv import load_dotenv
import os
import cv2
import google.generativeai as genai
from ultralytics import YOLO
from PIL import Image

load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-flash-latest')

# Get project root (Viscan/api)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "ml_models", "best.pt")
yolo_model = YOLO(MODEL_PATH)
# -----------------------------------

def get_gemini_ocr(cropped_image):
    """
    Sends the cropped plate image to Gemini 3 Flash.
    Gemini 3 handles fine text (OCR) much better than 1.5.
    """
    print("Sending cropped plate image to Gemini API for OCR...")
    
    # Convert BGR (OpenCV) to RGB (PIL)
    color_converted = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(color_converted)
    
    print("1")
    # Updated Prompt for Gemini 3
    prompt = "Read the characters on this vehicle license plate. Output ONLY the alphanumeric text. No spaces, no symbols."
    
    response = gemini_model.generate_content([prompt, pil_img])
    print(response.text.strip())
    return response.text.strip()

def extract_plate(image_path):
    """
    Detect plate using YOLO and extract text using Gemini API
    """
    image_path = os.path.abspath(image_path).replace("\\", "/") 
    img = cv2.imread(image_path)

    if img is None:
        print(f"Error: Could not read image at {image_path}")
        return None

    results = yolo_model(image_path)

    for r in results:
        boxes = r.boxes.xyxy.cpu().numpy()

        for box in boxes:
            x1, y1, x2, y2 = map(int, box)
            plate_crop = img[y1:y2, x1:x2]

            try:
                plate_text = get_gemini_ocr(plate_crop)
                # Cleaning up potential newlines or extra text
                return "".join(plate_text.split()) 
            except Exception as e:
                print(f"Gemini API Error: {e}")
                return None

    return None



