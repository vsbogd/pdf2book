# Overview

Script tries to automatically find pages to be splitted and splits
them. It adds a blank page after the title page if required to ensure the splitted pages
are properly aligned after converting to the Brochure mode. Then it adds required
number of empty pages at the end to have right number of pages. Finally it
forms the PDF which contains original pages in Brochure mode. 

To print this file print odd pages first then turn over the paper and print even
pages.

# Installation

```sh
pip install -r requirements.txt
```

# Usage

Run script:
```sh
python pdf2book.py <input.pdf> <output.pdf>
```

Get help:
```sh
python pdf2book.py --help
```

