#!/usr/bin/env python3
"""
docker_repo_mirror.py
Mirrors Docker CE repositories for RHEL 8, 9, and 10.
"""
import subprocess
import tempfile
import shutil
import logging
import sys
from pathlib import Path

# Configure standard output logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Configuration Variables
VERSIONS = ['8', '9', '10']
BASE_URL = "https://download.docker.com/linux/centos"
OUT_DIR = Path("./docker-ce-offline").resolve()
TAR_NAME = "docker-ce-offline-repos.tar.gz"

def check_dependencies():
    """Ensure all required system binaries are available."""
    for cmd in ['dnf', 'createrepo', 'tar']:
        if shutil.which(cmd) is None:
            logging.error(f"Required command '{cmd}' not found in PATH. Please install it.")
            sys.exit(1)

def create_repo_config(temp_dir, version):
    """Creates an isolated .repo file for the target OS version."""
    repoid = f"docker-ce-stable-{version}"
    repo_content = f"""[{repoid}]
name=Docker CE Stable - RHEL {version}
baseurl={BASE_URL}/{version}/x86_64/stable
enabled=1
gpgcheck=1
gpgkey={BASE_URL}/gpg
"""
    conf_path = temp_dir / f"{repoid}.repo"
    with open(conf_path, "w") as f:
        f.write(repo_content)
    return repoid

def main():
    logging.info("Starting offline repository mirroring...")
    check_dependencies()
    
    if OUT_DIR.exists():
        logging.info(f"Cleaning previous output directory: {OUT_DIR}")
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True)

    # Use a temporary directory to strictly isolate DNF configuration
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        logging.info(f"Created isolated DNF environment at {temp_path}")

        for ver in VERSIONS:
            logging.info(f"--- Processing RHEL {ver} ---")
            repoid = create_repo_config(temp_path, ver)
            ver_out_dir = OUT_DIR / f"rhel{ver}"
            ver_out_dir.mkdir()

            # 1. Synchronize repository
            reposync_cmd = [
                "dnf", "reposync",
                f"--setopt=reposdir={temp_path}", # Only load the temp repo we just made
                "--disablerepo=*",
                f"--enablerepo={repoid}",
                "--download-metadata",
                "--arch=x86_64",
                "--forcearch=x86_64",
                "-p", str(ver_out_dir)
            ]
            
            logging.info(f"Downloading packages and metadata for RHEL {ver}...")
            try:
                subprocess.run(reposync_cmd, check=True, stdout=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                logging.error(f"dnf reposync failed for RHEL {ver}. Check your connection or URL.")
                sys.exit(1)

            # 2. Create local repository metadata
            # reposync creates a subfolder named after the repoid
            repo_target_dir = ver_out_dir / repoid
            if not repo_target_dir.exists():
                repo_target_dir = ver_out_dir # Fallback for older DNF behavior

            logging.info(f"Generating offline repository metadata...")
            createrepo_cmd = ["createrepo", str(repo_target_dir)]
            try:
                subprocess.run(createrepo_cmd, check=True, stdout=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                logging.error(f"createrepo failed for RHEL {ver}.")
                sys.exit(1)

    # 3. Package the repositories
    logging.info("Compressing the mirrored repositories into a tarball...")
    tar_cmd = ["tar", "-czf", TAR_NAME, "-C", str(OUT_DIR.parent), OUT_DIR.name]
    try:
        subprocess.run(tar_cmd, check=True)
    except subprocess.CalledProcessError:
        logging.error("Failed to create the final tar.gz archive.")
        sys.exit(1)

    # Clean up the uncompressed directory to save space
    shutil.rmtree(OUT_DIR)
    logging.info(f"Process complete. Archive ready for transfer: {Path(TAR_NAME).resolve()}")

if __name__ == "__main__":
    main()