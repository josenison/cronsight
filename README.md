# cronsight

> Terminal dashboard for monitoring and auditing cron job execution history across remote servers

---

## Installation

```bash
pip install cronsight
```

Or install from source:

```bash
git clone https://github.com/youruser/cronsight.git && cd cronsight && pip install .
```

---

## Usage

Connect to a remote server and launch the dashboard:

```bash
cronsight --host user@192.168.1.10
```

Monitor multiple servers defined in a config file:

```bash
cronsight --config servers.yaml
```

Filter by job name and display the last 7 days of execution history:

```bash
cronsight --host user@myserver.com --job backup --since 7d
```

The interactive terminal UI lets you scroll through job runs, inspect exit codes, view stdout/stderr output, and flag anomalies — all without leaving your terminal.

---

## Configuration

Create a `servers.yaml` file to manage multiple hosts:

```yaml
servers:
  - name: web-01
    host: user@web01.example.com
  - name: db-01
    host: user@db01.example.com
```

---

## Requirements

- Python 3.8+
- SSH access to target servers
- `cron` or compatible scheduler on remote hosts

---

## License

This project is licensed under the [MIT License](LICENSE).