import requests
import os

def fetch_student_photo(photo_filename, save_dir="student_photos"):
    """
    Downloads a student photo from BPUT sites by trying multiple potential paths.
    """
    if not photo_filename:
        print("No photo filename provided.")
        return False

    # Potential base URLs where BPUT might store photos
    base_urls = [
        "https://results.bput.ac.in",
        "https://bputexam.in/Photo",
        "https://www.bput.ac.in/photos",
        "https://bputevaluation.com/student_photos",
        "http://results.bput.ac.in"
    ]
    
    # Ensure save directory exists
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    save_path = os.path.join(save_dir, photo_filename)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    }

    for base in base_urls:
        url = f"{base}/{photo_filename}"
        try:
            print(f"Trying to download from: {url}")
            response = requests.get(url, headers=headers, timeout=5, stream=True)
            
            if response.status_code == 200:
                # Check if it's actually an image and not a 404 page returned as 200
                content_type = response.headers.get('Content-Type', '')
                if 'image' in content_type:
                    with open(save_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    print(f"SUCCESS: Photo saved to {save_path}")
                    return True
                else:
                    print(f"Skipping: URL returned 200 but Content-Type is {content_type} (not an image).")
            else:
                print(f"Failed: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"Error trying {url}: {str(e)}")

    print("\n--- ALL PATHS FAILED ---")
    print("This confirms why it doesn't show in the UI either. The image might be missing from the server.")
    return False

if __name__ == "__main__":
    # Test with the filename found in the student_info for 2301230101
    example_photo = "100124161653353.jpg" 
    fetch_student_photo(example_photo)
