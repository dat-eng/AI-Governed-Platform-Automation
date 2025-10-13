# 🛠️ SAS Python Automation Toolkit

Modular automation toolkit for infrastructure provisioning in Nutanix, Infoblox and Ansible using GitHub, Python and YAML-based configuration.

---

## 🗂️ Directory Structure for sas-client Package

```
├── examples
│   ├──config                              # Sample YAML config files
│      ├── nutanix.yaml
│      ├── ...
├── Makefile                               # Makefile for installing virtual env etc
├── README.md                              # Documentation
├── requirements.txt                       # Dependencies 
├── setup.py                               # Python package definition
└── src                                    # Core automation modules
    └── sas_client
        ├── api
        │   ├── common
        │   │   ├── api_client.py
        │   │   └── __init__.py
        │   ├── nutanix.py
        │   ├── ...
        ├── cli.py                         # CLI entry point
        ├── __init__.py
        ├── utils                          # Utility functions
        │   ├── __init__.py
        │   ├── logger.py
        │   └── ...
        └── __version__.py
```

---

## ⚙️ Configuration

All sample configurations are in the `examples/config/` directory as YAML files.  
Each automation module (e.g., Nutanix, Infoblox) reads from its respective file:

```yaml
# config/nutanix.yaml
base_url: https://calm.example.com/api/nutanix/v3
username: your_user
os_type: rhel
...
```

---

## 🚀 Running the CLI

You can run launcher either:

### 1️⃣ As a Python package 

#### 📦 Installation

##### 🔹 Option 1: Install with Makefile to use python virtual environment

```bash
git clone git@github.enterprise.irs.gov:terraform/sas_python.git
cd sas_python
make init
source .venv/bin/activate
```

For local changes to take effect:
```bash
make build
```

For cleaning up the cache etc:
```bash
make clean
```

For deactivating and exiting the virtual environment:
```bash
deactivate
```

##### 🔹 Option 2: Install in-place (editable) manually

This installs the package in editable mode, so local changes take effect immediately.

```bash
git clone git@github.enterprise.irs.gov:terraform/sas_python.git
cd sas_python
pip install -e .
```

##### 🔹 Option 3: Install as a standard package manually

```bash
pip install .
```

#### 📦 Invoke the installed package

```bash
launcher nutanix -config <path to config/nutanix.yaml>
```

Use help to get all supported api's using launcher package:
```bash
launcher --help
```

#### 📦 Uninstall Package

This is only for the manual install without Makefile

```bash
pip uninstall api
```

### 2️⃣ Directly using Python (no installation needed) 

Use the main.py entry point to launch a specific module:

```bash
python main.py nutanix -config <path to config/nutanix.yaml>
```

---

## 🧰 Utility Modules

Located in `src/sas_client/utils/`:

- `logger.py` – metadata logging
- `hostname_generator.py` – logic for generating compliant hostnames
- `utils.py` – reusable helpers 

---

## ✅ Python Compatibility

- Python 3.8+
- `requests`, `pyyaml`, `logging`, and standard libraries

---