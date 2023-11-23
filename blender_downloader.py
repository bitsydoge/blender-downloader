#!/usr/bin/env python
"""
A simple script to download latest build of any version of Blender from their build website.

Usage: blender_downloader.py <version> [--os OS] [--base-dir BASE_DIR] [--url URL]

Author: bitsydoge

Source: https://github.com/bitsydoge/blender-downloader

Licence: Refer to the accompanying LICENSE.md file in this repository that correspond to a standard MIT licencing.
"""
import argparse
import os
import platform
import shutil
import tempfile

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from zipfile import ZipFile

AVAILABLE_OS_CONFIGS = {"windows": "C:/Program Files/Blender Foundation", "linux": "/usr/local/blender", "macos": "/Applications/Blender.app"}


def is_valid_zip(file_path):
    try:
        with ZipFile(file_path, "r") as zip_file:
            zip_file.namelist()
        return True
    except Exception as e:
        return False


# Command-line arguments
parser = argparse.ArgumentParser(description="Download and install the latest Blender build.")
parser.add_argument("version", type=str, help="Blender version to download and install")
parser.add_argument("--os", type=str, choices=AVAILABLE_OS_CONFIGS.keys(), help="Operating system")
parser.add_argument("--base-dir", type=str, help="Base directory for Blender installation")
parser.add_argument("--url", type=str, default="https://builder.blender.org/download/daily/", help="URL to parse")
args = parser.parse_args()

# Detect OS
if args.os is None:
    args.os = platform.system().lower()
if args.os.lower() not in AVAILABLE_OS_CONFIGS.keys():
    print(f"Unsupported operating system: {args.os}")
    exit(1)

# Find blender dir
if args.base_dir is None:
    base_dir = AVAILABLE_OS_CONFIGS[args.os]
else:
    base_dir = args.base_dir

# Check if have write access to install dir
try:
    with open(os.path.join(base_dir, "_temp_test.txt"), "w") as temp_file:
        temp_file.write("TEST")
except IOError:
    print(f"You do not have write permission in the directory: {base_dir}")
    print("Please restart the script as admin or select a different target directory with --base-dir argument")
    exit(1)
else:
    os.remove(os.path.join(base_dir, "_temp_test.txt"))

latest_dir = os.path.join(base_dir, f"Blender {args.version}")
version_file = os.path.join(latest_dir, ".blender_build")

# Send an http GET request
print("Fetching the download page...")
response = requests.get(args.url)

# Create a BeautifulSoup object and specify the parser
soup = BeautifulSoup(response.text, "html.parser")
no_version_found = True
print("Looking for the latest version...")
for link in soup.find_all("a"):
    file_url = link.get("href")
    if f"blender-{args.version}" in file_url and f"{args.os}" in file_url and file_url.endswith(".zip"):
        no_version_found = False
        # Check if this version has already been installed
        if os.path.exists(version_file):
            with open(version_file, "r") as file:
                if file.read() == file_url:
                    print("No new version available.")
                    break
        print(f"Found the latest version: {file_url}")

        # Download zip
        download_path = os.path.join(tempfile.gettempdir(), os.path.basename(file_url))
        if not os.path.exists(download_path) or not is_valid_zip(download_path):
            if os.path.exists(download_path):
                os.remove(download_path)

            print("Downloading archive...")
            file_data = requests.get(file_url, stream=True)
            total_size_in_bytes = int(file_data.headers.get("content-length", 0))
            progress_bar = tqdm(total=total_size_in_bytes, unit="iB", unit_scale=True)
            with open(download_path, "wb") as file:
                for chunk in file_data.iter_content(chunk_size=8192):
                    progress_bar.update(len(chunk))
                    file.write(chunk)
            progress_bar.close()

        # Extract zip
        print("Extracting archive...")
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                if os.path.exists(latest_dir):
                    shutil.rmtree(latest_dir, onerror=lambda func, path, exc_info: print(f"Error removing {path}: {exc_info[1]}"))
                os.makedirs(latest_dir, exist_ok=True)
            except Exception as e:
                print(f"An error occurred: {e}")
            with ZipFile(download_path, "r") as zip_ref:
                zip_ref.extractall(temp_dir)
            extracted_folder = os.path.join(temp_dir, os.listdir(temp_dir)[0])
            for item in os.listdir(extracted_folder):
                shutil.move(os.path.join(extracted_folder, item), latest_dir)

        # Save this build number to file
        with open(version_file, "w") as file:
            file.write(file_url)

        print(f"Blender {args.version} lastest build downloaded and installed successfully!")
        break

if no_version_found:
    print("This version cannot be found")
