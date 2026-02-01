
from rembg import remove
from PIL import Image
import io


def remove_background(input_path, output_path):
   # Load the input image
   with open(input_path, 'rb') as i:
       input_image = i.read()


   # Use rembg to remove the background
   output_image = remove(input_image)


   # Save the result
   with open(output_path, 'wb') as o:
       o.write(output_image)
  
   print(f"Background removed successfully! Saved to: {output_path}")


# USE IT LIKE THIS:
remove_background(
   "/content/sample_data/image_1.jpeg",
   "/content/sample_data/no_bg.png"  # Must save as .png for transparency
)
