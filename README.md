
# Docker CE Offline Repository Mirror

This project provides an automated, reliable Python script to mirror the official Docker CE repositories for RHEL 8, RHEL 9, and RHEL 10. It is specifically designed for Systems Administrators managing air-gapped or restricted offline networks.

The script safely isolates its `dnf` configuration to prevent polluting the host machine, synchronizes the required packages and metadata, generates local offline repository data, and compresses everything into a single archive ready for transfer.

## Features
* **Multi-OS Support:** Pulls repositories for RHEL 8, 9, and 10 simultaneously.
* **Host Isolation:** Uses temporary directories to ensure your host's standard `dnf` configuration remains untouched.
* **Storage Optimized:** Specifically targets the `x86_64` architecture to save bandwidth and disk space.
* **Ready-to-Deploy:** Automatically runs `createrepo` and packages the output into a `.tar.gz` archive.

## Prerequisites (Bridge Machine)

The machine running this script must have internet access and the following packages installed:

```bash
sudo dnf install -y python3 dnf-plugins-core createrepo_c tar
```

## Usage

1. Clone or download the `mirror_docker.py` script to your internet-connected bridge machine.
2. Make the script executable (optional but recommended):
   ```bash
   chmod +x mirror_docker.py
   ```
3. Run the script:
   ```bash
   python3 mirror_docker.py
   ```

The script will output progress logs to the console. Once complete, you will find a file named `docker-ce-offline-repos.tar.gz` in your current working directory.

## Offline Deployment

Once you have transferred `docker-ce-offline-repos.tar.gz` across your air-gap, follow these steps to serve and consume the packages.

### 1. Host the Repository
Extract the archive onto your internal web server (e.g., Apache, Nginx) or a centralized NFS share:

```bash
# Example: Extracting to an Apache web root
sudo tar -xzf docker-ce-offline-repos.tar.gz -C /var/www/html/
```

### 2. Configure Client Machines
On your offline RHEL nodes, create a new `.repo` file pointing to your internal server. 

Create `/etc/yum.repos.d/docker-ce-offline.repo`:

```ini
[docker-ce-offline]
name=Docker CE Offline - RHEL $releasever
baseurl=http://<YOUR_INTERNAL_SERVER_IP>/rhel$releasever/docker-ce-stable-$releasever/
enabled=1
gpgcheck=0
```
*(Note: Replace `<YOUR_INTERNAL_SERVER_IP>` with your actual server address or FQDN).*

### 3. Install Docker
With the repository configured, you can now install Docker normally:

```bash
sudo dnf clean all
sudo dnf install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

## Troubleshooting

* **Missing Command Errors:** Ensure `dnf`, `reposync`, `createrepo`, and `tar` are in your system's PATH. 
* **Incomplete Sync:** If the script fails during the `dnf reposync` phase, verify your bridge machine's internet connection and ensure no corporate firewalls are blocking `download.docker.com`.
```