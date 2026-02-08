import sys
import os

# Add skill script path
sys.path.append(os.path.abspath(".agent/skills/read_word_docs/scripts"))
try:
    from read_docx import read_docx
except ImportError:
    # If import fails (e.g. dependencies), we might need to rely on the script running it.
    # But read_docx checks for docx, so it should be fine if installed.
    # The script has a structure: install_and_import
    pass

# We can also just read the file manually if we want to be safe, but let's reuse
# We need to make sure we don't print to stdout again to avoid noise
# read_docx function PRINTS and returns.

# Let's just redefine a silent version or capture stdout
from io import StringIO
import contextlib

@contextlib.contextmanager
def capture_stdout():
    new_out = StringIO()
    old_out = sys.stdout
    try:
        sys.stdout = new_out
        yield new_out
    finally:
        sys.stdout = old_out

file_path = "docs/4.13_附件4   臺灣期貨交易所波動率指數_0708.docx"

if os.path.exists(file_path):
    # We will import inside here to ensure path is set
    from read_docx import read_docx
    
    # Capture output to avoid double printing and just save to file
    with capture_stdout() as captured:
        content = read_docx(file_path)
    
    # If the function returns None or empty, use captured output
    if not content:
        content = captured.getvalue()

    with open("vix_content_utf8.txt", "w", encoding="utf-8") as f:
        f.write(content)
    print("Content saved to vix_content_utf8.txt")
else:
    print(f"File not found: {file_path}")
