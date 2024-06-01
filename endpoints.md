---

## Endpoints

### 1. `/iso`

**Description:** Fetch a list of available ISO files on the Proxmox server.

**Method:** GET

**Parameters:** None

**Response:**
- `200 OK`: Returns a JSON object containing the list of available ISO files.
- `401 Unauthorized`: If authentication fails.

### 2. `/vm/create`

**Description:** Create a new virtual machine on the Proxmox server.

**Method:** POST

**Parameters:**
- `name` (string): Name of the VM to be created.
- `template` (string): Template for the VM (e.g., `ubuntu-20.04-template`).
- `storage` (string): Storage location for the VM disk.
- `memory` (integer): Amount of memory (in MB) for the VM.
- `cores` (integer): Number of CPU cores for the VM.
- `password` (string): Root password for the VM.

**Response:**
- `200 OK`: Returns a JSON object with the details of the created VM.
- `400 Bad Request`: If any required parameter is missing or invalid.
- `401 Unauthorized`: If authentication fails.

### 3. `/vm/start`

**Description:** Start a virtual machine on the Proxmox server.

**Method:** POST

**Parameters:**
- `vmid` (string): ID of the VM to be started.

**Response:**
- `200 OK`: If the VM is successfully started.
- `400 Bad Request`: If the VM ID is missing or invalid.
- `401 Unauthorized`: If authentication fails.

### 4. `/vm/stop`

**Description:** Stop a running virtual machine on the Proxmox server.

**Method:** POST

**Parameters:**
- `vmid` (string): ID of the VM to be stopped.

**Response:**
- `200 OK`: If the VM is successfully stopped.
- `400 Bad Request`: If the VM ID is missing or invalid.
- `401 Unauthorized`: If authentication fails.

### 5. `/vm/delete`

**Description:** Delete a virtual machine from the Proxmox server.

**Method:** POST

**Parameters:**
- `vmid` (string): ID of the VM to be deleted.

**Response:**
- `200 OK`: If the VM is successfully deleted.
- `400 Bad Request`: If the VM ID is missing or invalid.
- `401 Unauthorized`: If authentication fails.

---
