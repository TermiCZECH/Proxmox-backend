---

# Flask-based Backend API for Proxmox Server Management

## Overview

This Flask-based backend API facilitates the management of a Proxmox server, offering endpoints for various operations such as creating, starting, stopping, and deleting virtual machines (VMs), fetching ISO files, and checking the status of the Proxmox server. Built with simplicity and efficiency in mind, this API streamlines Proxmox server management tasks.

## Features

- **ISO File Management**: Fetch a list of available ISO files on the Proxmox server.
- **VM Management**: Create, start, stop, and delete VMs on the Proxmox server.
- **Server Status**: Check the status of the Proxmox server.
- **Authentication and Logging**: Secure API endpoints with authentication and log important information and errors for debugging purposes.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Usage](#usage)
5. [Endpoints](#endpoints)
6. [Security Considerations](#security-considerations)
7. [Contributing](#contributing)
8. [License](#license)

## Prerequisites

Before using this API, ensure you have the following prerequisites installed:

- Python 3.x
- Flask
- Requests
- Flask-CORS
- Python-dotenv

## Installation

Clone this repository to your local machine:

```bash
git clone https://github.com/your-username/your-repository.git
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Before running the API, configure the environment variables in the `.env` file:

- `API_PASSWORD`: Password for API authentication
- `PROXMOX_URL`: URL of the Proxmox server
- `PROXMOX_USER`: Proxmox username
- `PROXMOX_PASS`: Proxmox password
- `NODE_NAME`: Name of the Proxmox node
- `VERIFY_SSL`: Flag to toggle SSL verification (true/false)

## Usage

To start the Flask server, execute the `main` function:

```bash
python main.py
```

The API will perform pre-checks and then start the Flask server on `0.0.0.0:8080`.

## Endpoints

Explore the available endpoints and their functionalities in the [Endpoints Documentation](endpoints.md) section of the documentation.

## Security Considerations

When deploying this API, consider the following security best practices:

- Secure sensitive environment variables.
- Implement proper access controls to restrict unauthorized access to API endpoints.
- Regularly update dependencies to mitigate security vulnerabilities.

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests to improve this project.

## License

This project is licensed under the [MIT License](LICENSE).

---
