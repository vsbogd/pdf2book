# Software required

- pdftoppm - to convert a pdf to a list of PPM images, can be installed as part
of poppler package
- imagemagick - to manupulate images and convert to pdf file

# Usage

```
$ ./pdf2book <input.pdf> <output.pdf>
```

Script tries to automatically find which pages should be splitted and splits
them. Then it adds required number of empty pages at the end to have right
number of pages. Then it forms the PDF which contains original pages in
Brochure mode. 

To print this file print odd pages first then turn over paper and print even
pages.


