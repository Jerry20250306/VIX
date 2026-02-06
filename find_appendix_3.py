from docx import Document
import sys

def find_appendix_3(path):
    sys.stdout.reconfigure(encoding='utf-8')
    try:
        doc = Document(path)
    except Exception as e:
        print(f"Error loading doc: {e}")
        return

    found = False
    count = 0
    
    print("Searching for '附錄3'...")
    
    for i, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        
        # Check if this paragraph IS the title "附錄3"
        if "附錄3" in text or "附錄 3" in text:
            print(f"\n=== FOUND at paragraph {i}: {text} ===")
            found = True
            count = 0 # Reset count to print content after THIS occurrence
        
        if found:
            print(f"{i}: {text}")
            count += 1
            if count > 80: # Read more lines to cover the "3 steps"
                found = False # Stop printing for this occurrence
                count = 0

if __name__ == "__main__":
    if len(sys.argv) > 1:
        find_appendix_3(sys.argv[1])
    else:
        print("Please provide a file path")
