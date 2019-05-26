import io
import pdf2image
import PIL as pil
import argparse
from sklearn.cluster import KMeans
import numpy as np
import logging

def pdf_to_pages(file):
    images = pdf2image.convert_from_bytes(file.read())
    return list(map(Page, images))

class Page:

    def __init__(self, image, parent=None):
        self.image = image
        self.parent = parent

    def save(self, filename):
        self.image.save(filename)

    def size(self):
        return self.image.size

    def split(self):
        (width, height) = self.size()
        mid_x = width // 2
        return [Page(self.image.crop((0, 0, mid_x, height)), self),
                Page(self.image.crop((mid_x+1, 0, width, height)), self)]

    def blank(self):
        blank_image = self.image.copy()
        (width, height) = self.size()
        blank_image.paste((255, 255, 255), (0, 0, width, height))
        return Page(blank_image)

    @staticmethod
    def merge(left, right):
        (left_w, left_h) = left.size()
        (right_w, right_h) = right.size()
        (width, height) = (left_w + right_w, max(left_h, right_h))
        image = pil.Image.new("RGB", (width, height))
        image.paste((255, 255, 255), (0, 0, width, height))
        image.paste(left.image, (0, 0))
        image.paste(right.image, (left_w, 0))
        return Page(image)

    def resize(self, width=None, height=None):
        size = None
        if width is None and height is None:
            raise ValueError("Either 'width' or 'height' argument should " +
                             "be passed")
        if height is None:
            height = int(width / ratio(self.size()))
        if width is None:
            width = int(height * ratio(self.size()))
        return Page(self.image.resize((width, height)), self.parent)

def find_single_pages(pages):
    sizes = np.array(list(map(lambda size: [ratio(size)],
                              map(Page.size, pages))))
    logging.debug("sizes: " + str(sizes))
    kmeans = KMeans(n_clusters=2, random_state=0).fit(sizes)
    logging.debug("kmeans.labels_: " + str(kmeans.labels_))
    smallest = min(enumerate(kmeans.cluster_centers_),
                   key=lambda pair : pair[1])[0]
    return list(map(lambda label : label == smallest, kmeans.labels_))

def ratio(size):
    (width, height) = size
    return width / height

def square(size):
    (width, height) = size
    return width * height

def split_pages(src, force=False):
    if force:
        single_flags = [ False ] * len(src)
    else:
        single_flags = find_single_pages(src)
    dst = []
    for (single, page) in zip(single_flags, src):
        if single:
            dst.append(page)
        else:
            dst.extend(page.split())
    return dst

def resize_pages(src):
    max_height = max([page.size()[1] for page in src])
    dst = [page.resize(height=max_height) for page in src]
    return dst

def align_double_pages(src):
    pairs = rearrange_pages(src)
    (left, right) = pairs[-1]
    if left.parent == right.parent:
        return src
    logging.info("adding blank page to align double pages")
    first_page = src[0]
    dst = [first_page] + [first_page.blank()] + src[1:]
    return dst

def add_blank(src, after_last = True):
    pages_num = len(src)
    count = (4 - pages_num % 4) % 4
    logging.info("original number of pages: " + str(pages_num) +
                 ", number of blank pages to add: " + str(count))
    last_page = src[-1]
    blank = last_page.blank()
    if after_last:
        dst = src + [blank] * count
    else:
        dst = src[:-1] + [blank] * count + [last_page]
    return dst

def save_pages(pages):
    i = 0
    for page in pages:
        page.save("%04d" % i + ".png")
        i += 1

def rearrange_pages(src):
    dst = []
    begin = 0
    end = len(src) - 1
    twist = True
    while begin < end:
        if twist:
            pair = (src[end], src[begin])
        else:
            pair = (src[begin], src[end])
        dst.append(pair)
        twist = not twist
        begin += 1
        end -= 1
    return dst

def pairs_to_pages(pairs):
    return [Page.merge(pair[0], pair[1]) for pair in pairs]

def pages_to_pdf(file, pages):
    images = list(map(lambda page : page.image, pages))
    images[0].save(file, save_all=True, append_images=images[1:])

def parse_args():
    parser = argparse.ArgumentParser(description="Convert PDF to book")
    parser.add_argument("input", type=str, help="input PDF file")
    parser.add_argument("output", type=str, help="output PDF file")
    parser.add_argument("--log-level", type=str, help="logging level",
            default="INFO")
    parser.add_argument("--blank-after-last", action="store_true",
            help="insert blank pages after last one", default=False)
    parser.add_argument("--mode", type=str, default="auto",
            help="pages splitting mode: auto - determine double pages " +
            "automatically, single - single pages only, double - double " +
            "pages only")
    return parser.parse_args()

args = parse_args()
logging.basicConfig(level=getattr(logging, args.log_level.upper()))

with open(args.input, "rb") as input:
    pages = pdf_to_pages(input)
    if args.mode != "single":
        pages = split_pages(pages, force=args.mode=="auto")
    pages = resize_pages(pages)
    pages = align_double_pages(pages)
    pages = add_blank(pages, after_last=args.blank_after_last)
    pairs = rearrange_pages(pages)
    pages = pairs_to_pages(pairs)
    with open(args.output, "wb") as output:
        pages_to_pdf(output, pages)

