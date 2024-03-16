#!/usr/bin/env python3

import argparse
import os
import sys
import tempfile
from PIL import Image
import qrcode
from pathlib import Path
import magic  # Import the magic library

# Set up argument parser
parser = argparse.ArgumentParser(description='Generate or process a QR code.')
parser.add_argument('input', type=str, help='Text to generate a QR code from, or the filename of a QR code image to be processed.')
parser.add_argument('--output', '-o', type=str, help='Output file to write the result to (optional).')
parser.add_argument('--verbose', '-v', action='store_true', help='Increase output verbosity.')
args = parser.parse_args()

# Function to print messages to stderr if verbose is True
def eprint(*func_args, **kwargs):
    if args.verbose:
        print("[+]", *func_args, file=sys.stderr, **kwargs)

input_path = Path(args.input)

# Function to determine if the file is an image
def is_image_file(filepath):
    mime = magic.Magic(mime=True)
    mime_type = mime.from_file(str(filepath))
    return mime_type.startswith('image/')

using_temp_file = False
# Try to process the input as an image file
if input_path.is_file() and is_image_file(input_path):
    img = Image.open(args.input).convert('L')
elif not input_path.exists():
    using_temp_file = True
    # Input is treated as text for QR code generation
    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(args.input)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        qr_temp_filename = temp_file.name
        if args.verbose:
            eprint(f"Generated QR code saved to temporary file {qr_temp_filename}")
        img.save(qr_temp_filename)
        img = Image.open(qr_temp_filename).convert('L')
else:
    eprint("The provided input is not a valid file path and is not suitable for QR code generation.")
    sys.exit(1)

pixels = img.load()
width, height = img.size

# Initialize bounding box coordinates
min_x, max_x = width, 0
min_y, max_y = height, 0

# Threshold value to distinguish between black and white
binary_threshold = 128

# Find the bounds of the QR code within the image
for y in range(height):
    for x in range(width):
        # If the pixel is darker than the threshold, it's considered black
        if pixels[x, y] < binary_threshold:
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)

# Find the first horizontal line of the QR code within the bounds
y = min_y
while y < max_y and pixels[min_x, y] > binary_threshold:
    y += 1

# Calculate the length of the first continuous horizontal black line (block size)
block_size = 0
while pixels[min_x, y] == 0:
    block_size += 1
    y += 1

# The block size is the length of the black line divided by 7 (as per QR specification)
block_size //= 7

# Initialize the list to hold the QR code data
qr_blocks = []

# Analyze the QR code and build the 2D array
for y in range(min_y, max_y, block_size):
    row = []
    for x in range(min_x, max_x, block_size):
        # Use the middle pixel of each block to determine the block's color
        middle_pixel_value = pixels[x + block_size // 2, y + block_size // 2]
        # A pixel value of 0 means black in grayscale
        is_black = 1 if middle_pixel_value == 0 else 0
        row.append(is_black)
    qr_blocks.append(row)

img.close()

black_block = '\u2588'*2
white_block = '\u2591'*2

if using_temp_file:
    os.unlink(qr_temp_filename)
    eprint(f"Temporary file {qr_temp_filename} has been deleted")

eprint(f"Outputting QRcode as Unicode characters.")
if args.output:
    with open(args.output, 'w') as file:
        for row in qr_blocks:
            for block in row:
                file.write(black_block if block == 1 else white_block)  # Using two spaces for white blocks
            file.write('\n')
else:
    # Print out the QR code in terminal
    for row in qr_blocks:
        for block in row:
            print(black_block if block == 1 else white_block, end='')  # Using two spaces for white blocks
        print()

