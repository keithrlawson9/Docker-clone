#!/usr/bin/env python3
"""
mirror_docker.py
Incrementally mirrors Docker CE repositories for RHEL 8, 9, and 10.
Optimized for scheduled tasks (Cron) in air-gapped environments.
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
OUT_DIR = Path("/opt/docker-ce-offline").resolve()
TAR_NAME = "/opt/docker-ce-offline-repos.tar.gz"

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
    logging.info("Starting incremental repository sync...")
    check_dependencies()
    
    # Ensure the persistent directory exists (DO NOT delete it between runs)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Use a temporary directory to strictly isolate DNF configuration
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        for ver in VERSIONS:
            logging.info(f"--- Processing RHEL {ver} ---")
            repoid = create_repo_config(temp_path, ver)
            ver_out_dir = OUT_DIR / f"rhel{ver}"
            ver_out_dir.mkdir(exist_ok=True)

            # 1. Synchronize repository (Incremental + Cleanup)
            reposync_cmd = [
                "dnf", "reposync",
                f"--setopt=reposdir={temp_path}", # Only load the temp repo we just made
                "--disablerepo=*",
                f"--enablerepo={repoid}",
                "--download-metadata",
                "--arch=x86_64",
                "--forcearch=x86_64",
                "--delete",        # Removes packages deleted from upstream
                "--newest-only",   # Keeps only the latest versions locally
                "-p", str(ver_out_dir)
            ]
            
            logging.info(f"Syncing packages for RHEL {ver}...")
            try:
                subprocess.run(reposync_cmd, check=True, stdout=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                logging.error(f"dnf reposync failed for RHEL {ver}. Check your connection or URL.")
                sys.exit(1)

            # 2. Update local repository metadata
            repo_target_dir = ver_out_dir / repoid
            if not repo_target_dir.exists():
                repo_target_dir = ver_out_dir # Fallback for older DNF behavior

            logging.info(f"Updating offline repository metadata...")
            # Use --update to only process changed packages, saving massive amounts of time
            createrepo_cmd = ["createrepo", "--update", str(repo_target_dir)]
            try:
                subprocess.run(createrepo_cmd, check=True, stdout=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                logging.error(f"createrepo failed for RHEL {ver}.")
                sys.exit(1)

    # 3. Package the repositories
    logging.info("Compressing the updated repositories into a tarball...")
    tar_cmd = ["tar", "-czf", TAR_NAME, "-C", str(OUT_DIR.parent), OUT_DIR.name]
    try:
        subprocess.run(tar_cmd, check=True)
    except subprocess.CalledProcessError:
        logging.error("Failed to create the final tar.gz archive.")
        sys.exit(1)

    logging.info(f"Sync complete. Updated archive ready for transfer: {TAR_NAME}")

if __name__ == "__main__":
    main()