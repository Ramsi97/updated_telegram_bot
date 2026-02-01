import cv2
import numpy as np
from PIL import Image

def convert_to_grayscale(pil_image):
    """Converts a PIL Image to an OpenCV grayscale image object."""
    # 1. Convert PIL image to a NumPy array (which OpenCV uses)
    open_cv_image = np.array(pil_image)
    
    # 2. Convert RGB to Grayscale
    # Note: PIL uses RGB, so we use COLOR_RGB2GRAY
    gray_image = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2GRAY)
    
    return gray_image

def convert_to_binary(pil_image):
    """Converts a PIL Image to a strict Black & White (Binary) image."""
    gray = convert_to_grayscale(pil_image)
    
    # Apply thresholding: pixels > 127 become white, others black
    _, binary_image = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    
    return binary_image