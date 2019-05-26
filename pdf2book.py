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

    def __init__(self, image):
        self.image = image

    def save(self, filename):
        self.image.save(filename)

    def size(self):
        return self.image.size

    def split(self):
        (width, height) = self.size()
        mid_x = width // 2
        return [Page(self.image.crop((0, 0, mid_x, height))),
                Page(self.image.crop((mid_x+1, 0, width, height)))]

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

def find_single_pages(pages):
    sizes = np.array(list(map(lambda x: [ratio(x)], map(Page.size, pages))))
    logging.debug("sizes: " + str(sizes))
    kmeans = KMeans(n_clusters=2, random_state=0).fit(sizes)
    logging.debug("kmeans.labels_: " + str(kmeans.labels_))
    smallest = min(enumerate(kmeans.cluster_centers_),
                   key=lambda x : x[1])[0]
    return list(map(lambda x : x == smallest, kmeans.labels_))

def ratio(size):
    (width, height) = size
    return width / height

def square(size):
    (width, height) = size
    return width * height

def split_pages(src):
    single_flags = find_single_pages(src)
    dst = []
    for (single, page) in zip(single_flags, src):
        if single:
            dst.append(page)
        else:
            dst.extend(page.split())
    return dst

def add_blank(src, after_last = True):
    pages_num = len(src)
    count = (4 - pages_num % 4) % 4
    logging.info("original number of pages: " + str(pages_num) +
                 ", number of blank pages to add: " + str(count))
    last_page = src[pages_num - 1]
    blank = last_page.blank()
    if after_last:
        dst = src + [blank] * count
    else:
        dst = src[:pages_num - 1] + [blank] * count + [last_page]
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
            page = Page.merge(src[end], src[begin])
        else:
            page = Page.merge(src[begin], src[end])
        dst.append(page)
        twist = not twist
        begin += 1
        end -= 1
    return dst

def pages_to_pdf(file, pages):
    images = list(map(lambda x : x.image, pages))
    images[0].save(file, save_all=True, append_images=images[1:])

def parse_args():
    parser = argparse.ArgumentParser(description="Convert PDF to book")
    parser.add_argument("input", type=str, help="input PDF file")
    parser.add_argument("output", type=str, help="output PDF file")
    parser.add_argument("--log-level", type=str, help="logging level",
            default="INFO")
    parser.add_argument("--blank-after-last", action="store_true",
            help="insert blank pages after last one", default=False)
    return parser.parse_args()

args = parse_args()
logging.basicConfig(level=getattr(logging, args.log_level.upper()))

with open(args.input, "rb") as input:
    pages = pdf_to_pages(input)
    pages = split_pages(pages)
    pages = add_blank(pages, after_last=args.blank_after_last)
    pages = rearrange_pages(pages)
    with open(args.output, "wb") as output:
        pages_to_pdf(output, pages)

