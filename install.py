
import os
import subprocess
import requests
import zipfile
import shutil
import stat
import sys

# --- Configuration ---
XRAY_VERSION = "v1.8.10"
HIDDIFY_VERSION = "v3.2.0"

XRAY_URL = f"https://github.com/XTLS/Xray-core/releases/download/{XRAY_VERSION}/Xray-linux-64.zip"
HIDDIFY_URL = f"https://github.com/hiddify/hiddify-core/releases/download/{HIDDIFY_VERSION}/hiddify-linux-amd64.zip"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CORES_DIR = os.path.join(BASE_DIR, "cores")
TMP_DIR = os.path.join(BASE_DIR, "tmp_setup")
VENV_DIR = os.path.join(BASE_DIR, ".venv")

XRAY_ZIP_PATH = os.path.join(TMP_DIR, "xray.zip")
HIDDIFY_ZIP_PATH = os.path.join(TMP_DIR, "hiddify.zip")

XRAY_BINARY_PATH = os.path.join(CORES_DIR, "xray-core")
HIDDIFY_BINARY_PATH = os.path.join(CORES_DIR, "hiddify-cli")

# --- Color Codes ---
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
NC = "\033[0m"

# --- Helper Functions ---

def print_step(message):
    print(f"\n{YELLOW}➡️  {message}{NC}")

def print_success(message):
    print(f"{GREEN}✅ {message}{NC}")

def print_error(message):
    print(f"{RED}❌ {message}{NC}")
    sys.exit(1)

def run_command(command):
    try:
        subprocess.run(command, check=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {command}\nStdout: {e.stdout.decode()}\nStderr: {e.stderr.decode()}")
        return False

def download_file(url, dest_path):
    print_step(f"Downloading {url} to {dest_path}")
    try:
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print_success("Download complete.")
        return True
    except requests.exceptions.RequestException as e:
        print_error(f"Failed to download {url}: {e}")
        return False

def extract_zip(zip_path, dest_dir, binary_name, final_name):
    print_step(f"Extracting {zip_path}")
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            # Find the binary in the zip file
            binary_path_in_zip = None
            for name in zip_ref.namelist():
                if binary_name.lower() in name.lower() and not name.endswith("/"):
                     binary_path_in_zip = name
                     break
            
            if not binary_path_in_zip:
                print_error(f"Could not find '{binary_name}' in {zip_path}")

            # Extract the binary
            zip_ref.extract(binary_path_in_zip, dest_dir)
            
            # Rename and move
            extracted_path = os.path.join(dest_dir, binary_path_in_zip)
            final_path = os.path.join(dest_dir, final_name)
            shutil.move(extracted_path, final_path)

            print_success(f"Extracted and moved to {final_path}")
            return True

    except (zipfile.BadZipFile, KeyError) as e:
        print_error(f"Failed to extract {zip_path}: {e}")
        return False

def make_executable(path):
    print_step(f"Making {path} executable")
    try:
        st = os.stat(path)
        os.chmod(path, st.st_mode | stat.S_IEXEC)
        print_success(f"{path} is now executable.")
        return True
    except OSError as e:
        print_error(f"Failed to make {path} executable: {e}")
        return False

# --- Main Setup ---
def main():
    print_step("🚀 Starting V2Ray Scanner Ultimate Setup")

    # 1. Create directories
    os.makedirs(CORES_DIR, exist_ok=True)
    os.makedirs(TMP_DIR, exist_ok=True)
    
    # 2. Download Cores
    download_file(XRAY_URL, XRAY_ZIP_PATH)
    download_file(HIDDIFY_URL, HIDDIFY_ZIP_PATH)

    # 3. Extract Cores
    extract_zip(XRAY_ZIP_PATH, CORES_DIR, "xray", "xray-core")
    extract_zip(HIDDIFY_ZIP_PATH, CORES_DIR, "hiddify-cli", "hiddify-cli")

    # 4. Make binaries executable
    make_executable(XRAY_BINARY_PATH)
    make_executable(HIDDIFY_BINARY_PATH)

    # 5. Create and activate virtual environment
    print_step("Creating Python virtual environment")
    if not os.path.exists(VENV_DIR):
        run_command(f"{sys.executable} -m venv {VENV_DIR}")

    # Determine the correct pip path
    pip_executable = os.path.join(VENV_DIR, "bin", "pip")

    # 6. Install Python dependencies
    print_step("Installing Python dependencies from requirements.txt")
    run_command(f"{pip_executable} install --upgrade -r requirements.txt")

    # 7. Final cleanup
    print_step("Cleaning up temporary files")
    shutil.rmtree(TMP_DIR)
    print_success("Cleanup complete.")

    print_success("\n🎉 Setup complete! You can now run the scanner. 🎉")
    print_success(f"To run manually, activate the virtual environment: \n  source {os.path.join(VENV_DIR, 'bin', 'activate')}")
    print_success("Then, see the README.md for instructions.")


if __name__ == "__main__":
    main()
