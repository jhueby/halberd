# Halberd BAS

Open-source Breach and Attack Simulation for small teams.

Halberd gives you automated adversary simulation mapped to [MITRE ATT&CK](https://attack.mitre.org/) without the six-figure price tag of commercial BAS platforms. Run atomic techniques or full attack chains against your endpoints, see what your EDR catches, and identify coverage gaps before an attacker does.

## Features

- **Two test libraries** — individual atomic techniques (15+ ATT&CK-mapped tests) and multi-step attack chains (ransomware, DNS exfil, persistence)
- **Import attack chains** — load chains from YAML files or URLs; document-to-chain conversion planned for v2
- **Safe by default** — risk levels, cleanup commands, dry-run mode, root protection
- **Web dashboard** — ATT&CK coverage heatmap, campaign management, test results
- **CLI-first** — run tests directly from the terminal without the server
- **Lightweight agent** — polls a server for tasks, reports results, works through NAT
- **Zero infrastructure** — SQLite database, single Python package, Docker one-liner

## Install

### pip (recommended)

```bash
pip install -e ".[server]"
```

### Docker

```bash
docker compose up -d
# Dashboard at http://localhost:8000
```

### Linux .deb

```bash
cd packaging
./build-deb.sh
sudo dpkg -i halberd-bas_0.1.0_all.deb
```

### Windows .exe

```cmd
cd packaging\windows
build.bat
REM Output: packaging\windows\dist\halberd.exe
```

## Quick Start

### List available techniques

```bash
halberd list
```

### Run a technique (dry run)

```bash
halberd run T1082 --dry-run
```

### Run an attack chain

```bash
halberd run chain-dns-exfil --dry-run
```

### Import a chain from URL

```bash
halberd import https://raw.githubusercontent.com/yourorg/chains/main/apt-sim.yml
```

### Start the dashboard

```bash
halberd server
# Open http://127.0.0.1:8000
```

### Start an agent (connects to server)

```bash
halberd agent --server-url http://server:8000 --api-key YOUR_KEY
```

## Library

### Atomic Techniques

| ID | Name | Tactic | Risk |
|----|------|--------|------|
| T1059.004 | Unix Shell Execution | execution | safe |
| T1053.003 | Cron Job Persistence | persistence | low |
| T1003.008 | Shadow File Read | credential-access | low |
| T1048.001 | DNS Exfiltration | exfiltration | medium |
| T1082 | System Information Discovery | discovery | safe |
| T1016 | Network Configuration Discovery | discovery | safe |
| T1033 | System Owner/User Discovery | discovery | safe |
| T1087.001 | Local Account Enumeration | discovery | safe |
| T1518.001 | Security Software Discovery | discovery | safe |
| T1070.004 | Indicator Removal - File Deletion | defense-evasion | low |
| T1105 | Ingress Tool Transfer | command-and-control | medium |
| T1027 | Base64 Obfuscation | defense-evasion | safe |
| T1071.001 | HTTP C2 Beacon | command-and-control | medium |
| T1046 | Network Service Scan | discovery | medium |
| T1222.002 | File Permission Modification | defense-evasion | low |

### Attack Chains

| ID | Name | Tactics |
|----|------|---------|
| chain-ransomware-sim | Ransomware Simulation | discovery, credential-access, defense-evasion |
| chain-dns-exfil | Data Exfiltration via DNS | discovery, exfiltration |
| chain-persistence-backdoor | Persistence and C2 Backdoor | execution, persistence, command-and-control |

## Importing Chains

Halberd supports importing attack chains from external sources:

```yaml
# my-chain.yml
id: chain-custom-apt
name: "Custom APT Simulation"
description: "Recon, persistence, exfil"
mitre_tactics: [discovery, persistence, exfiltration]
steps:
  - technique: T1082
    delay_after: 5
  - technique: T1053.003
    delay_after: 10
  - technique: T1048.001
```

```bash
halberd import my-chain.yml
halberd import https://example.com/chain.yml --type url
```

**v2 planned**: Upload a threat report or blog post URL and Halberd will automatically extract the attack chain, mapping described steps to MITRE ATT&CK techniques.

## Safety

- **Risk levels**: Each test is tagged `safe`, `low`, `medium`, or `high`
- **Max risk**: Agent enforces a configurable ceiling (`--max-risk medium`)
- **Cleanup**: Tests include reversal commands that run automatically
- **Dry run**: `--dry-run` shows commands without executing
- **Root protection**: Agent refuses to run as root unless `--allow-root` is passed

## Architecture

```
halberd/
├── library/          # Atomic tests + attack chains (YAML)
│   ├── atomic/       # ATT&CK-mapped techniques
│   └── chains/       # Multi-step scenarios
├── agent/            # Test runner + server client
├── server/           # FastAPI + dashboard
│   ├── routes/       # REST API
│   └── templates/    # Web UI (Jinja2 + htmx)
└── report/           # Coverage report generator
```

## API

When the server is running, full API docs are at `http://localhost:8000/docs` (Swagger UI).

Key endpoints:
- `GET /api/library/techniques` — list atomic techniques
- `GET /api/library/chains` — list attack chains
- `POST /api/library/import` — import a chain
- `POST /api/campaigns` — create a test campaign
- `GET /api/results/coverage` — ATT&CK coverage data

## Contributing

1. Fork the repo
2. Add techniques to `halberd/library/atomic/` following the YAML schema
3. Add chains to `halberd/library/chains/`
4. Run tests: `pip install -e ".[dev]" && pytest`
5. Submit a PR

## License

Apache 2.0
