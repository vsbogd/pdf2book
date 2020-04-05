# Copyright 2018, 2019 Vitaly Bogdanov
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import io
import pdf2image
import PIL as pil
import argparse
from sklearn.cluster import KMeans
import numpy as np
import logging

def pdf_to_pages(file):
    log().info("extract pages")
    images = pdf2image.convert_from_bytes(file.read())
    return list(map(lambda args: Page(str(args[0]), args[1]),
        zip(range(1, len(images)), images)))

class Page:

    def __init__(self, id, image, parent=None, position=None):
        self.id = id
        self.image = image
        self.parent = parent
        self.position = position
        log().debug("new page: " + str(self))

    def __str__(self):
        return str(self.id)

    def save(self, filename):
        self.image.save(filename)

    def size(self):
        return self.image.size

    def split(self):
        (width, height) = self.size()
        mid_x = width // 2
        return [Page(self.id + "l", self.image.crop((0, 0, mid_x, height)), self, "left"),
                Page(self.id + "r", self.image.crop((mid_x+1, 0, width, height)), self, "right")]

    def blank(self):
        blank_image = self.image.copy()
        (width, height) = self.size()
        blank_image.paste((255, 255, 255), (0, 0, width, height))
        return Page("e", blank_image)

    @staticmethod
    def merge(left, right):
        left_id = left.id
        right_id = right.id
        (left_w, left_h) = left.size()
        (right_w, right_h) = right.size()
        (width, height) = (left_w + right_w, max(left_h, right_h))
        image = pil.Image.new("RGB", (width, height))
        image.paste((255, 255, 255), (0, 0, width, height))
        image.paste(left.image, (0, 0))
        image.paste(right.image, (left_w, 0))
        return Page(left_id + "+" + right_id, image)

    def resize(self, width=None, height=None):
        size = None
        if width is None and height is None:
            raise ValueError("Either 'width' or 'height' argument should " +
                             "be passed")
        if height is None:
            height = int(width / ratio(self.size()))
        if width is None:
            width = int(height * ratio(self.size()))
        return Page(self.id, self.image.resize((width, height)), self.parent,
                self.position)

def find_single_pages(pages):
    sizes = np.array(list(map(lambda size: [ratio(size)],
                              map(Page.size, pages))))
    log().debug("sizes: " + str(sizes))
    kmeans = KMeans(n_clusters=2, random_state=0).fit(sizes)
    log().debug("kmeans.labels_: " + str(kmeans.labels_))
    smallest = min(enumerate(kmeans.cluster_centers_),
                   key=lambda pair : pair[1])[0]
    if (len(kmeans.cluster_centers_) == 1 or
            almost_equal(ratio(kmeans.cluster_centers_), 1.0)):
        if kmeans.cluster_centers_[0] <= 1.1:
            log().debug("all pages are single")
            return [ True ] * len(pages)
        else:
            log().debug("all pages are double")
            return [ False ] * len(pages)
    else:
        return list(map(lambda label : label == smallest, kmeans.labels_))

def almost_equal(a, b):
    return abs(a - b) < 0.1

def ratio(size):
    (width, height) = size
    return width / height

def square(size):
    (width, height) = size
    return width * height

def split_pages(src, force=False):
    log().info("split pages, force: " + str(force))
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
    log().info("resize pages")
    max_height = max([page.size()[1] for page in src])
    dst = [page.resize(height=max_height) for page in src]
    return dst

def align_double_pages(src):
    log().info("align double pages")
    dst = src
    while True:
        pairs = rearrange_pages(dst)
        (left, right) = pairs[-1]
        if left.parent == right.parent:
            return dst
        log().info("adding blank page to align double pages")
        first_page = dst[0]
        dst = [first_page] + [first_page.blank()] + dst[1:]

def add_blank(src, after_last = True):
    log().info("add blank pages")
    pages_num = len(src)
    count = (4 - pages_num % 4) % 4
    log().info("original number of pages: " + str(pages_num) +
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
    log().info("rearrange pages")
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
    images[0].save(file, format="pdf", save_all=True, append_images=images[1:])

def skip_pages(pages, to_skip):
    log().info("skip pages: " + str(to_skip))
    pages_enum = filter(lambda pair: (pair[0] + 1) not in to_skip, enumerate(pages))
    return list(map(lambda pair : pair[1], pages_enum))

def pdf_to_book(input, output, args):
    pages = pdf_to_pages(input)
    pages = skip_pages(pages, args.skip)
    if args.mode != "single":
        pages = split_pages(pages, force=args.mode!="auto")
    pages = resize_pages(pages)
    pages = align_double_pages(pages)
    pages = add_blank(pages, after_last=args.blank_after_last)
    pairs = rearrange_pages(pages)
    pages = pairs_to_pages(pairs)
    pages_to_pdf(output, pages)

def parse_args():
    parser = argparse.ArgumentParser(description="Convert PDF to book")
    parser.add_argument("input", type=str, help="input PDF file")
    parser.add_argument("output", type=str, help="output PDF file")
    parser.add_argument("--log-level", type=str, help="logging level",
            default="INFO")
    parser.add_argument("--blank-after-last", action="store_true",
            help="insert blank pages after last one", default=False)
    parser.add_argument("--mode", type=str, default="auto",
            choices=["auto", "single", "double"],
            help="pages splitting mode: auto - determine double pages " +
            "automatically, single - single pages only, double - double " +
            "pages only")
    parser.add_argument("--skip", type=int, nargs="+", default=[],
            help="pages to skip delimited by space")
    return parser.parse_args()

def log():
    return logging.getLogger("pdf2book")

if __name__ == "__main__":
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper()))

    with open(args.input, "rb") as input:
        with open(args.output, "wb") as output:
            pdf_to_book(input, output, args)
