#!/usr/bin/env python
import os
import re
import sys
import argparse
import subprocess
import epub

ENCODING = sys.getdefaultencoding()

MIMETYPES = {
    'application/pdf': '.pdf',
    'application/epub+zip': '.epub'
}

def import_ebook(filename):
    isbn = extract_isbn(filename)
    opf, cover = fetch_metadata(filename, isbn)
    calibre_id = add_to_library(filename, cover)
    apply_metadata(calibre_id, opf)
    return calibre_id

def tempfile(suffix):
    return subprocess.check_output(['mktemp', '-u', '--suffix', suffix]).decode(ENCODING).strip()

def determine_format(filename):
    extension = os.path.splitext(filename)[-1].lower()
    if extension in MIMETYPES.values():
        return extension

    mimetype = subprocess.check_output(['file', '-b', '-i', filename]).split(';')[0]
    try:
        return MIMETYPES[mimetype]
    except Exception as e:
        return None

def extract_isbn(filename):
    match = re.search('(\d{13}|\d{10})', filename)
    if match:
        return match.group()

    data_format = determine_format(filename)
    if data_format == '.pdf':
        command = ['pdftotext', '-f', '1', '-l', '10', filename, '-']
        text = subprocess.check_output(command, stderr=subprocess.PIPE).decode(ENCODING)
        match = re.search('(?:[0-9]{3}-)?[0-9]{1,5}-[0-9]{1,7}-[0-9]{1,6}-[0-9]', text)
        if match:
            return match.group().replace('-', '')
    elif data_format == '.epub':
        book = epub.open_epub(filename)
        identifiers = ' '.join(book.opf.metadata.identifiers[0])
        match = re.search('(\d{13}|\d{10})', identifiers)
        if match:
            return match.group()

    return None

def fetch_metadata(filename, isbn):
    opf = tempfile(".opf")
    cover = tempfile(".jpg")
    opf_text = subprocess.check_output(
        ['fetch-ebook-metadata', '-i', isbn, '-o', opf, '-c', cover]
    ).decode(ENCODING)
    with open(opf, 'w') as f:
        f.write(opf_text)
    return opf, cover

def add_to_library(filename, cover):
    output = subprocess.check_output(
        ['calibredb', 'add', filename, '-c', cover]
    ).decode(ENCODING)
    calibre_id = re.search('\d+', output).group(0)
    return calibre_id

def apply_metadata(calibre_id, opf):
    subprocess.check_output(
        ['calibredb', 'set_metadata', calibre_id, opf]
    )

def main():
    parser = argparse.ArgumentParser(prog="calibre-import", description="Fetch metadata and import ebooks to calibre")
    parser.add_argument('filename', nargs='+', help='ebook file to import')
    args = parser.parse_args()

    for filename in args.filename:
        calibre_id = import_ebook(filename)
        print("added", calibre_id, filename)

if __name__ == "__main__": main()
