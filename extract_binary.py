#!/usr/bin/env python
"""
This script will extract the game/mgs binary from input file.
"""

import xml.etree.ElementTree as ET
import os
import subprocess
from pathlib import Path
import datetime
import shutil
import argparse

MODULEDESCRIPTOR = "moduledescriptor.xml"
CURRENT_DIR = os.getcwd()
GAMES_DIR = "/games/games/"
MGS_DIR = "/games/"


def parse_args():
    parser = argparse.ArgumentParser(description="""
        This script will extract the game/mgs binary from input file.
        Input can be of type .img, .tgz, .7z or .zip.
        For game/MGS binary can be copied to /games folder by giving option [c] or [r]
        Required folder permissions will be set in that case.
        """, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('input_file', type=str,
                        help='Input image file of type .img, .tgz, .7z or .zip')
    parser.add_argument('-c', "--copy", action='store_true',
                        help='copy to /games (or /games/games/)')
    parser.add_argument('-r', "--replace", action='store_true',
                        help='copy to /games (or /games/games/) and replace existing')

    args = parser.parse_args()
    return args


class XmlParser:
    """
    Class to handle xml related operations
    """

    def __init__(self, inputfile):
        """
        Initializing class
        """
        if os.path.isfile(inputfile):
            self.inputfile = inputfile
            self.root_node = ET.parse(inputfile).getroot()
        else:
            raise ValueError("input file does not exist")

    def get_module(self):
        """
        To get the image type from moduledescriptor.xml file
        """
        for tag in self.root_node.findall('module'):
            # Get the value of the heading attribute
            module_type = tag.get('ModuleType')
            if module_type is not None:
                return module_type
            else:
                print("errr on reading ", MODULEDESCRIPTOR)

    def get_game_name(self):
        """
        To get the game name from moduledescriptor.xml file
        """
        for tag in self.root_node.findall('module'):
            # Get the value of the heading attribute
            module_install_path = tag.get('ModuleInstallPath')
            if module_install_path is not None:
                return os.path.basename(os.path.normpath(module_install_path))
            else:
                print("errr on reading ", MODULEDESCRIPTOR)


class ImageExtract:
    """
    Run the actual image extract.
    """

    def __init__(self, imagepath):
        """
        init function
        """
        if os.path.isfile(imagepath):
            self.imagepath = os.path.abspath(imagepath)
        else:
            raise ValueError("input file does not exist")
        self.items_to_clean = []

    def __del__(self):
        """
        desctroctr
        """
        self.do_cleanup()

    def do_cleanup(self):
        """
        """
        for item in self.items_to_clean:
            if os.path.isdir(item):
                shutil.rmtree(item)

    def check_report_error(self, result):
        """
        """
        if result.returncode:
            print(result)
            self.do_cleanup()
            raise RuntimeError(result.stdout)

    def check_prerequisites(self):
        """
        Check 7z is installed or not, if not install try to install.
        """
        result = subprocess.run(
            ["which", "7z"], capture_output=True, check=False, text=True)
        if result.returncode:
            print("7z not found, trying to install")
            result = subprocess.run(
                ["apt", "install", "p7zip-full", "-y"], capture_output=True, check=False)
            if result.returncode:
                print("7z install failed, please install it to proceed", result)
                return False
        return True

    def _mkdir(self):
        """
        create a new directory and returns its path
        """
        outdir = os.path.join(
            CURRENT_DIR, "out-" + datetime.datetime.now().strftime("%Y%b%d%H%M%S%f"))

        Path(outdir).mkdir(parents=True, exist_ok=True)
        return outdir

    def run(self, filepath=None):
        """
        To determine type of file and do the required operation for it
        """
        filepath = filepath if filepath else self.imagepath
        _, file_extension = os.path.splitext(filepath)
        outdir = self._mkdir()
        self.items_to_clean.append(outdir)
        image_file = ""
        if file_extension == ".tgz":
            result = subprocess.run(
                ["tar", "xzvf", filepath, "-C", outdir], capture_output=True, check=False)
            self.check_report_error(result)
            image_file = os.path.join(
                outdir, result.stdout.decode().split()[0])

        elif file_extension == ".zip" or file_extension == ".7z":
            newoutdir2 = self._mkdir()
            self.items_to_clean.append(newoutdir2)
            result = subprocess.run(
                ["7z", "x", filepath, "-o" + newoutdir2], capture_output=True, check=False)
            self.check_report_error(result)
            result = subprocess.run(
                ["ls", newoutdir2], capture_output=True, check=False)
            self.check_report_error(result)
            image_file = os.path.join(
                newoutdir2, result.stdout.decode().split()[0])

        elif file_extension == ".img":
            image_file = filepath

        return self.extract_img_file(image_file)

    def extract_img_file(self, image_file):
        """
        Extract from .img file
        """
        _, file_extension = os.path.splitext(image_file)
        if file_extension != ".img":
            self.do_cleanup()
            raise ValueError("incorrect file given ", image_file)

        print("Extracting ", image_file)

        if os.path.isfile(image_file):
            newoutdir = self._mkdir()
            self.items_to_clean.append(newoutdir)
            result = subprocess.run(
                ["7z", "x", image_file, "-o" + newoutdir], capture_output=True, check=False)
            self.check_report_error(result)

            zero_img = os.path.join(newoutdir, "0.img")
            if os.path.isfile(zero_img):
                newoutdir2 = self._mkdir()
                result = subprocess.run(
                    ["7z", "x", zero_img, "-o" + newoutdir2], capture_output=True, check=False)
                self.check_report_error(result)

                return newoutdir2
        return None


class BinaryCopy:
    """
    class to handle all the file copy operations
    """

    def __init__(self, module_type, theme_name, current_ext_path, copy=False, replace=False):
        """
        init function
        """
        self.module_type = module_type
        self.theme_name = theme_name
        self.current_ext_path = current_ext_path
        self.copy = copy
        self.replace = replace
        self.output_dir = ""
        print("Module Type is ", self.module_type)

        if self.module_type == "MULTI_GAME_UI":           
            self.output_dir = MGS_DIR
        elif self.module_type == "GAME":
            self.output_dir = GAMES_DIR
        else:
            raise ValueError("Copying not supported for type",
                             self.module_type)

        self.target = os.path.join(self.output_dir, self.theme_name)

    def run(self):
        """
        Call the copy function and print result
        """
        if self._run():
            print("Copied %s to %s successfully" % (self.theme_name, self.output_dir))
    def _run(self):
        """
        Do the copy 
        """
        if not os.path.isdir(GAMES_DIR):
            Path(GAMES_DIR).mkdir(parents=True, exist_ok=True)

        if self.replace:
            if os.path.isdir(self.target):
                shutil.rmtree(self.target)
            result = subprocess.run(
                ["mv", self.current_ext_path, self.output_dir], capture_output=True, check=False)
            return self.do_copy(result)

        elif self.copy:
            if os.path.isdir(self.target):
                print("directory exist, please copy manually", self.target)
                return
            result = subprocess.run(
                ["cp", "-rp", self.current_ext_path, self.output_dir], capture_output=True, check=False)
            return self.do_copy(result)
        return None

    def do_copy(self, result):
        """
        do the actual copy here
        """
        if result.returncode:
            print("copy failed, please copy manually", result)
            return False
        result = subprocess.run(
            ["chmod", "700", "-R", MGS_DIR], capture_output=True, check=False)
        if result.returncode:
            print("Please set enough permission for /games", result)
            return False
        return True


def main():

    args = parse_args()

    image_ext = ImageExtract(args.input_file)
    if not image_ext.check_prerequisites():
        return
    outdir = image_ext.run()
    module_file = os.path.join(outdir, MODULEDESCRIPTOR)
    xml_parser = XmlParser(module_file)
    theme_name = xml_parser.get_game_name()
    print("Theme name ", theme_name)
    gamedir = os.path.join(os.path.dirname(outdir), theme_name)
    if os.path.isdir(gamedir):
        shutil.rmtree(gamedir)
    subprocess.run(["mv", outdir, gamedir])
    print("successfully extracted the image to ", gamedir)

    module_type = xml_parser.get_module()
    if args.copy or args.replace:
        bc = BinaryCopy(module_type, theme_name,
                        gamedir, args.copy, args.replace)
        bc.run()


if __name__ == '__main__':
    main()
