# Backend API Documentation

## Overview
This backend API is built using Flask and is designed to interact with a Proxmox server. It provides various endpoints for managing virtual machines (VMs), fetching ISO files, and checking the status of the Proxmox server. The API also includes logging and authentication mechanisms.

## Table of Contents
1. [Environment Variables](#environment-variables)
2. [Logging](#logging)
3. [Authentication](#authentication)
4. [Endpoints](#endpoints)
   - [GET /api/iso](#get-apiiso)
   - [GET /api/status](#get-apistatus)
   - [POST /api/create-vm](#post-apicreate-vm)
   - [GET /api/nodes](#get-apinodes)
   - [GET /api/nodes/<node>/qemu](#get-apinodesnodeqemu)
   - [GET /api/nodes/<node>/qemu/<vmid>/status](#get-apinodesnodeqemuvmidstatus)
   - [POST /api/nodes/<node>/qemu/<vmid>/config](#post-apinodesnodeqemuvmidconfig)
   - [POST /api/nodes/<node>/qemu/<vmid>/status/start](#post-apinodesnodeqemuvmidstatusstart)
   - [POST /api/nodes/<node>/qemu/<vmid>/status/stop](#post-apinodesnodeqemuvmidstatusstop)
   - [DELETE /api/nodes/<node>/qemu/<vmid>](#delete-apinodesnodeqemuvmid)

## Environment Variables
The following environment variables must be set in the `.env` file:
- `API_PASSWORD`: Password for API authentication
- `PROXMOX_URL`: URL of the Proxmox server
- `PROXMOX_USER`: Proxmox username
- `PROXMOX_PASS`: Proxmox password
- `NODE_NAME`: Name of the Proxmox node
- `VERIFY_SSL`: Flag to toggle SSL verification (true/false)

## Logging
The API uses the `logging` module with `RotatingFileHandler` for logging information and errors. Logs are saved in `api_info.log` and `api_error.log`.

## Authentication
API requests to endpoints under `/api` (except `/api/status`) require an `Authorization` header with the format `Bearer <API_PASSWORD>`.

## Endpoints

### GET /api/iso
Fetches the list of ISO files available on the Proxmox server.

#### Response
- `200 OK`: Returns a list of ISO files.
- `500 Internal Server Error`: Failed to fetch the ISO list.

### GET /api/status
Checks the status of the API.

#### Response
- `200 OK`: Returns `{"status": "API is running"}`.

### POST /api/create-vm
Creates a new VM with the specified name, ISO, and tier.

#### Request Body
```json
{
    "name": "vm_name",
    "iso": "iso_file",
    "tier": "basic|standard|performance"
}
```

#### Response
- `200 OK`: Returns the response from the Proxmox server.
- `400 Bad Request`: Invalid tier.
- `500 Internal Server Error`: Failed to create the VM.

### GET /api/nodes
Fetches the list of nodes from the Proxmox server.

#### Response
- `200 OK`: Returns a list of nodes.
- `500 Internal Server Error`: Failed to fetch the nodes.

### GET /api/nodes/<node>/qemu
Fetches the list of VMs on a specified node.

#### Response
- `200 OK`: Returns a list of VMs.
- `500 Internal Server Error`: Failed to fetch the VMs.

### GET /api/nodes/<node>/qemu/<vmid>/status
Fetches the status of a specified VM on a specified node.

#### Response
- `200 OK`: Returns the VM status.
- `500 Internal Server Error`: Failed to fetch the VM status.

### POST /api/nodes/<node>/qemu/<vmid>/config
Updates the configuration of a specified VM on a specified node.

#### Request Body
- JSON object containing configuration parameters.

#### Response
- `200 OK`: Returns the response from the Proxmox server.
- `500 Internal Server Error`: Failed to update the VM configuration.

### POST /api/nodes/<node>/qemu/<vmid>/status/start
Starts a specified VM on a specified node.

#### Response
- `200 OK`: Returns the response from the Proxmox server.
- `500 Internal Server Error`: Failed to start the VM.

### POST /api/nodes/<node>/qemu/<vmid>/status/stop
Stops a specified VM on a specified node.

#### Response
- `200 OK`: Returns the response from the Proxmox server.
- `500 Internal Server Error`: Failed to stop the VM.

### DELETE /api/nodes/<node>/qemu/<vmid>
Deletes a specified VM on a specified node.

#### Response
- `200 OK`: Returns the response from the Proxmox server.
- `500 Internal Server Error`: Failed to delete the VM.

## Pre-checks
Before starting the Flask server, the application performs pre-checks to ensure connectivity with the Proxmox server, ISO fetch functionality, and VM creation capability.

## Running the Application
To run the application, execute the `main` function. The application will perform pre-checks and then start the Flask server on `0.0.0.0:5000`.

```python
if __name__ == "__main__":
    main()
```

## Notes
- SSL verification can be disabled by setting `VERIFY_SSL` to `false`.
- Logs are essential for tracking API usage and debugging issues.
- Ensure that the `.env` file is properly configured before running the application.

## Conclusion
This documentation provides an overview of the backend API built with Flask. It includes details on environment variables, logging, authentication, endpoints, and pre-checks. Ensure proper configuration and perform necessary checks before deploying the application.
