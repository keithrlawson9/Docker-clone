```markdown
# Docker CE Incremental Offline Mirror

This project provides an automated, cron-ready Python script to incrementally mirror the official Docker CE repositories for RHEL 8, 9, and 10. It is designed for Systems Administrators managing air-gapped or restricted offline networks who need to keep internal packages up to date without wasting bandwidth or disk space.

Unlike standard mirror scripts, this tool maintains a persistent local cache. On subsequent runs, it only downloads new packages, deletes obsolete packages that no longer exist upstream, and rapidly updates the XML metadata before packaging everything into a transfer-ready archive.

## Key Features
* **Incremental Syncing:** Uses the `--newest-only` and `--delete` flags to keep the local mirror clean and prevent storage bloat.
* **Fast Metadata Generation:** Uses `createrepo --update` to only scan package changes, drastically reducing execution time on recurring runs.
* **Multi-OS Support:** Pulls repositories for RHEL 8, 9, and 10 simultaneously.
* **Host Isolation:** Uses temporary directories to ensure your bridge machine's standard `dnf` configuration remains untouched.
* **Storage Optimized:** Specifically targets the `x86_64` architecture.

## Prerequisites (Bridge Machine)

The machine running this script must have internet access and the following packages installed:

```bash
sudo dnf install -y python3 dnf-plugins-core createrepo_c tar
```

## Setup & Configuration

By default, the script uses `/opt/` to store its persistent data and the final tarball. Ensure the user running the script has write permissions to this directory, or run it via `sudo`.

1. Place the `mirror_docker.py` script in a logical location, such as `/opt/scripts/`.
2. Make the script executable:
   ```bash
   chmod +x /opt/scripts/mirror_docker.py
   ```

## Usage

### Manual Execution
To trigger a sync manually, simply run the script:
```bash
sudo /opt/scripts/mirror_docker.py
```
Upon completion, your updated package archive will be located at `/opt/docker-ce-offline-repos.tar.gz`.

### Automated Execution (Cron)
To set this up as a "set it and forget it" task that runs every two weeks:

1. Open your crontab editor:
   ```bash
   sudo crontab -e
   ```
2. Add the following line to run the script at 2:00 AM on the 1st and 15th of every month, routing logs to a dedicated file:
   ```bash
   0 2 1,15 * * /usr/bin/python3 /opt/scripts/mirror_docker.py >> /var/log/docker_mirror.log 2>&1
   ```

## Offline Deployment

Once you have transferred `docker-ce-offline-repos.tar.gz` across your air-gap, follow these steps to serve and consume the packages.

### 1. Host the Repository
Extract the archive onto your internal web server (e.g., Apache, Nginx) or a centralized NFS share. Because the script outputs a single root folder (`docker-ce-offline`), it will cleanly overwrite the existing files when extracted.

```bash
# Example: Extracting to an internal web root
sudo tar -xzf docker-ce-offline-repos.tar.gz -C /var/www/html/
```

### 2. Configure Client Machines
On your offline RHEL nodes, point `dnf` to your internal server. 

Create `/etc/yum.repos.d/docker-ce-offline.repo`:

```ini
[docker-ce-offline]
name=Docker CE Offline - RHEL $releasever
baseurl=http://<YOUR_INTERNAL_SERVER_IP>/docker-ce-offline/rhel$releasever/docker-ce-stable-$releasever/
enabled=1
gpgcheck=0
```
*(Note: Replace `<YOUR_INTERNAL_SERVER_IP>` with your actual server address or FQDN).*

### 3. Install or Update Docker
With the repository configured, you can install or update Docker normally:

```bash
sudo dnf clean all
sudo dnf update docker-ce docker-ce-cli containerd.io
```