import os
import platform
import requests
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

# --- Configuration ---
BASE_DIR = Path(__file__).parent.resolve()
CORES_DIR = BASE_DIR / "cores"

XRAY_REPO = "XTLS/Xray-core"
HIDDIFY_REPO = "hiddify/hiddify-core"


# --- Color Codes for Output ---
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    ENDC = "\033[0m"


def print_color(text, color):
    print(f"{color}{text}{Colors.ENDC}")


def get_system_info():
    """Detects the OS and architecture."""
    os_type = platform.system().lower()
    arch = platform.machine().lower()

    if os_type not in ["linux", "darwin"]:
        raise NotImplementedError(f"Unsupported OS: {os_type}")

    if "aarch64" in arch or "arm64" in arch:
        arch = "arm64-v8a" if os_type == "linux" else "arm64"
    elif "x86_64" in arch or "amd64" in arch:
        arch = "64"
    else:
        raise NotImplementedError(f"Unsupported architecture: {arch}")

    return os_type, arch


def get_latest_release_asset_url(repo, keyword):
    """Finds the download URL for the latest release asset matching the keyword."""
    print_color(f"🔍 Searching for latest release of {repo}...", Colors.BLUE)
    api_url = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        assets = response.json()["assets"]
        for asset in assets:
            if keyword in asset["name"]:
                print_color(f"✅ Found asset: {asset['name']}", Colors.GREEN)
                return asset["browser_download_url"]
        raise FileNotFoundError(f"No asset found for keyword '{keyword}' in {repo}")
    except requests.RequestException as e:
        raise ConnectionError(f"Failed to fetch release info from GitHub API: {e}")


def download_and_unzip(url, target_dir, binary_name):
    """Downloads a zip file, extracts a specific binary, and makes it executable."""
    target_dir.mkdir(parents=True, exist_ok=True)
    zip_path = target_dir / Path(url).name
    binary_path = target_dir / binary_name

    print_color(f"Downloading {url}...", Colors.BLUE)
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(zip_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
    except requests.RequestException as e:
        raise ConnectionError(f"Failed to download file: {e}")

    print_color("Unpacking archive...", Colors.BLUE)
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        # Find the binary in the zip file and extract it
        for member in zip_ref.namelist():
            if binary_name in member and not member.endswith(".sig"):
                with zip_ref.open(member) as source, open(binary_path, "wb") as target:
                    shutil.copyfileobj(source, target)
                break
        else:
            raise FileNotFoundError(
                f"Could not find '{binary_name}' in the downloaded archive."
            )

    os.remove(zip_path)
    os.chmod(binary_path, 0o755)  # Make it executable
    print_color(
        f"✨ Successfully installed {binary_name} to {binary_path}", Colors.GREEN
    )


def install_dependencies():
    """Installs Python packages from requirements.txt."""
    print_color("🐍 Installing Python dependencies...", Colors.BLUE)
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
        )
        print_color("✅ Dependencies installed successfully.", Colors.GREEN)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to install Python packages: {e}")


def main():
    """Main installation function."""
    print_color("🚀 Starting Professional Proxy Installer...", Colors.YELLOW)
    try:
        os_type, arch = get_system_info()
        print_color(f"System detected: {os_type.capitalize()} {arch}", Colors.BLUE)

        # --- Install Xray-core ---
        xray_keyword = f"{os_type}-{arch}.zip"
        xray_url = get_latest_release_asset_url(XRAY_REPO, xray_keyword)
        download_and_unzip(xray_url, CORES_DIR, "xray")

        # --- Install hiddify-core ---
        # Note: Hiddify has a different naming scheme
        hiddify_arch = {"64": "amd64", "arm64": "arm64"}.get(arch, arch)
        hiddify_keyword = f"{os_type}-{hiddify_arch}"
        hiddify_url = get_latest_release_asset_url(HIDDIFY_REPO, hiddify_keyword)
        download_and_unzip(hiddify_url, CORES_DIR, "hiddify")

        # --- Install Python Deps ---
        install_dependencies()

        print_color(
            "🎉 All components installed successfully! You are ready to go.",
            Colors.GREEN,
        )

    except (NotImplementedError, FileNotFoundError, ConnectionError, RuntimeError) as e:
        print_color(f"❌ Installation failed: {e}", Colors.RED)
        sys.exit(1)
    except Exception as e:
        print_color(f"An unexpected error occurred: {e}", Colors.RED)
        sys.exit(1)


if __name__ == "__main__":
    main()
