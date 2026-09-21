# 530_2026_09_conference - Conference Management System

A web application for managing conferences, built for CSC 530 Software Engineering.

## Tech Stack

- Frontend: HTML / CSS / JavaScript
- Backend: Python / Flask / Blueprint
- Database: MySQL
- Dev DB: `edwardhunter`
- UAT DB: `fall2026_530_conf`
- Connector: `mysql-connector-python`
- Project Folder: `fall2026_530_conf`

## Prerequisites

- Python 3.x
- MySQL
- Git

## How to Run the Project

### 1. Clone the Repository

Clone the project from GitHub:

```bash
git clone git@github.com:krispepper/530_2026_09_conference.git
```

### 2. Enter the Project Folder

Navigate to the project directory:

```bash
cd 530_2026_09_conference
```

### 3. Create a Virtual Environment

Create a Python virtual environment:

```bash
python3 -m venv .venv
```

### 4. Activate the Virtual Environment

#### macOS / Linux / Compsci Server

```bash
source .venv/bin/activate
```

#### Windows Command Prompt

```bash
.venv\Scripts\activate.bat
```

After activation, `(.venv)` should appear at the beginning of the command prompt.

### 5. Install Dependencies

Install all required Python dependencies from `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 6. Run the Application

Make sure the virtual environment is activated:

```bash
source .venv/bin/activate
```

If the dependencies have not already been installed:

```bash
pip install -r requirements.txt
```

Run the application using the project's run script:

```bash
./run.sh
```

If permission to execute the script is required:

```bash
chmod +x run.sh
./run.sh
```

The terminal should display the host and port where the Flask application is running.

> **Note:** The Flask application is currently under development. These instructions describe how the application will be launched once the Flask setup is complete.
