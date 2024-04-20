#!/usr/bin/env python3

import argparse
import os
import sys
import tempfile
from PIL import Image
import qrcode
from pathlib import Path
import magic  # Import the magic library

class Converter:
    """
    class designed to convert a QR code to unicode.
    """

    # set class variables. the dunder marks them as "private".
    __black_block = '\u2588'*2
    __white_block = '\u2591'*2

    # Threshold value to distinguish between black and white
    __binary_threshold = 128

    def __init__(self, input:str, output:str=None, verbose:bool=None):
        # if verbose option is not provided, set default to false.
        if verbose is None:
            verbose = False

        # type verification for verbose option.
        if not(isinstance(verbose,bool)):
            raise TypeError(f"verbose must be a boolean. got {type(verbose)}")
        
        # if output is not provided, set default to an empty string.
        if output is None:
            output = str()

        # type verification for output option.
        if not(isinstance(output,str)):
            raise TypeError(f"output must be a string. got {type(output)}")
        
        # type verification for input. this argument is required.
        if not(isinstance(input,str)):
            raise TypeError(f"input must be a string. got {type(input)}")
        
        # set instance variables.
        self.input = Path(input.strip())
        self.output = output.strip()
        self.verbose = verbose

        # private instance variables
        self.__tmp_filename = str()
        self.__using_temp_file = bool()

        return
    
    # Function designed to build a temporary file.
    def __build_temp_file(self):
        img = None
        message = str()
        success = bool()

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(self.input)
                qr.make(fit=True)

                img = qr.make_image(fill_color="black", back_color="white")
                self.__tmp_filename = temp_file.name

                if self.verbose:
                    self.__eprint(f"Generated QR code saved to temporary file {self.__tmp_filename}")

                img.save(self.__tmp_filename)
                img = Image.open(self.__tmp_filename).convert('L')

            message = "temp file successfully built"
            success = True
        except Exception as ex:
            message = str(ex)
            success = False

        return (img, success, message)
    
    # Function to print messages to stderr if verbose is True
    def __eprint(self, *func_args, **kwargs):
        if self.verbose:
            print("[+]", *func_args, file=sys.stderr, **kwargs)
    
    # Function to determine if the file is an image
    def __is_image_file(self):
        mime = magic.Magic(mime=True)
        mime_type = mime.from_file(self.input)
        return mime_type.startswith('image/')
    
    # Function designed to carry out the main logic for conversion.
    def convertQRCode(self):
        height = int()
        max_x = int()
        max_y = int()
        message = str()
        min_x = int()
        min_y = int()
        qr_blocks = list()
        success = bool()
        width = int()

        try:
            if self.input.is_file() and self.__is_image_file(self.input):
                img = Image.open(self.input).convert('L')
            elif not(self.input.exists()):
                self.__using_temp_file = True

                img, success, message = self.__build_temp_file()
                if not(success):
                    raise ValueError(message)
            else:
                raise ValueError("The provided input is not a valid file path and is not suitable for QR code generation.")

            pixels = img.load()
            width, height = img.size

            # Initialize bounding box coordinates
            min_x, max_x = width, 0
            min_y, max_y = height, 0

            # Find the bounds of the QR code within the image
            for y in range(height):
                for x in range(width):
                    # If the pixel is darker than the threshold, it's considered black
                    if pixels[x, y] < self.__binary_threshold:
                        min_x = min(min_x, x)
                        max_x = max(max_x, x)
                        min_y = min(min_y, y)
                        max_y = max(max_y, y)

            # Find the first horizontal line of the QR code within the bounds
            y = min_y
            while y < max_y and pixels[min_x, y] > self.__binary_threshold:
                y += 1

            # Calculate the length of the first continuous horizontal black line (block size)
            block_size = 0
            while pixels[min_x, y] == 0:
                block_size += 1
                y += 1

            # The block size is the length of the black line divided by 7 (as per QR specification)
            block_size //= 7

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

            if self.__using_temp_file:
                os.unlink(self.__tmp_filename)
                self.__eprint(f"Temporary file {self.__tmp_filename} has been deleted")

            self.__eprint(f"Outputting QRcode as Unicode characters.")
            if len(self.output) > 0:
                with open(self.output, 'w') as file:
                    for row in qr_blocks:
                        for block in row:
                            file.write(self.__black_block if block == 1 else self.__white_block)  # Using two spaces for white blocks
                        file.write('\n')
            else:
                # Print out the QR code in terminal
                for row in qr_blocks:
                    for block in row:
                        print(self.__black_block if block == 1 else self.__white_block, end='')  # Using two spaces for white blocks
                    print()

            message = "qr code successfully converted"
            success = True
        except Exception as ex:
            message = str(ex)
            success = False

        return (success, message)

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Generate or process a QR code.')
    parser.add_argument('input', type=str, help='Text to generate a QR code from, or the filename of a QR code image to be processed.')
    parser.add_argument('--output', '-o', type=str, help='Output file to write the result to (optional).')
    parser.add_argument('--verbose', '-v', action='store_true', help='Increase output verbosity.')
    args = parser.parse_args()

    try:
        converter = Converter(args.input, args.output, args.verbose)

        success, message = converter.convertQRCode()
        if not(success):
            raise ValueError(message)
        
        print(f"[+] {message}")
    except Exception as ex:
        print(f"[-] {message}")
        sys.exit(1)

    return

# added so this can be imported into other projects.
if __name__ == "__main__":
    main()

