---
name: read_word_docs
description: utility skill to read Microsoft Word (.docx) files, including paragraphs and tables
---

# `read_word_docs` Skill

This skill allows you to read the contents of a `.docx` file using a Python script. It extracts both paragraph text and table data, formatting them legibly.

## Capability
- Reads basic text paragraphs.
- Iterate through tables and prints them row by row.
- Handles `python-docx` dependency installation automatically.

## Usage

To read a word document, run the `read_docx.py` script located in the `scripts` directory of this skill.

### Command

```powershell
python .agent/skills/read_word_docs/scripts/read_docx.py "path/to/your/file.docx"
```

### Example

```powershell
python .agent/skills/read_word_docs/scripts/read_docx.py "選擇權序列價格篩選機制.docx"
```

## Requirements
- Python 3
- `python-docx` (will be installed automatically if missing)
