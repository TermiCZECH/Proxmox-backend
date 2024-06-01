from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import urllib3
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from functools import wraps
import threading
import time
import json
import os

# Load configuration from .env file
load_dotenv()

# Configuration
REQUESTS_PER_MINUTE = 60
RETRY_INTERVAL = 5  # in seconds

# Rate limiting setup
request_timestamps = []
lock = threading.Lock()

# Flag to toggle SSL verification
VERIFY_SSL = os.getenv('VERIFY_SSL', 'false').lower() == 'true'

if not VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
CORS(app)
#CORS(app, resources={r"/api/*": {"origins": "http://127.0.0.1:5000"}})

# Setup logging
info_handler = RotatingFileHandler('api_info.log', maxBytes=100000, backupCount=3)
info_handler.setLevel(logging.INFO)
info_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
info_handler.setFormatter(info_formatter)

error_handler = RotatingFileHandler('api_error.log', maxBytes=100000, backupCount=3)
error_handler.setLevel(logging.ERROR)
error_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
error_handler.setFormatter(error_formatter)

app.logger.addHandler(info_handler)
app.logger.addHandler(error_handler)
app.logger.setLevel(logging.INFO)

# Load environment variables
PROXMOX_URL = os.getenv('PROXMOX_URL')
PROXMOX_USER = os.getenv('PROXMOX_USER')
PROXMOX_PASS = os.getenv('PROXMOX_PASS')
PASSWORD = os.getenv('API_PASSWORD')
NODE_NAME = os.getenv('NODE_NAME')
VERIFY_SSL = os.getenv('VERIFY_SSL', 'false').lower() == 'true'
TOTAL_CPU_THREADS = int(os.getenv('TOTAL_CPU_THREADS', 48))
TOTAL_MEMORY_GB = int(os.getenv('TOTAL_MEMORY_GB', 48))
PROXMOX_CPU_OVERHEAD_THREADS = int(os.getenv('PROXMOX_CPU_OVERHEAD_THREADS', 2))
PROXMOX_MEMORY_OVERHEAD_GB = int(os.getenv('PROXMOX_MEMORY_OVERHEAD_GB', 6))

# Function to get Proxmox ticket and CSRF token
def get_proxmox_ticket():
    url = f"{PROXMOX_URL}/access/ticket"
    data = {
        'username': PROXMOX_USER,
        'password': PROXMOX_PASS
    }
    response = requests.post(url, data=data, verify=VERIFY_SSL)
    response.raise_for_status()
    result = response.json()
    return result['data']['ticket'], result['data']['CSRFPreventionToken']

# Function to check Proxmox connection
def check_proxmox_connection():
    while True:
        try:
            # Replace with actual Proxmox connection check
            response = requests.get(f"{PROXMOX_URL}/api2/json/version", verify=VERIFY_SSL)
            if response.status_code == 200:
                print("Connected to Proxmox")
                break
        except requests.RequestException as e:
            print(f"Failed to connect to Proxmox: {e}")
        time.sleep(RETRY_INTERVAL)

# Start Proxmox connection check in a separate thread
threading.Thread(target=check_proxmox_connection, daemon=True).start()

# Function to continuously check if proxmox is running
def check_proxmox_status():
    while True:
        try:
            response = requests.get(f"{PROXMOX_URL}/api2/json/version", verify=VERIFY_SSL)
            if response.status_code == 200:
                return True
            else:
                return False
        except requests.exceptions.RequestException:
            return False
        finally:
            time.sleep(10)

# Function to check rate limiting
def is_rate_limited():
    with lock:
        current_time = time.time()
        # Remove timestamps older than a minute
        while request_timestamps and request_timestamps[0] < current_time - 60:
            request_timestamps.pop(0)
        if len(request_timestamps) >= REQUESTS_PER_MINUTE:
            return True
        request_timestamps.append(current_time)
        return False
    
# Decorator for rate limiting
def rate_limited(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if is_rate_limited():
            return jsonify({"error": "Too many requests, please try again later."}), 429
        return f(*args, **kwargs)
    return decorated_function

# Middleware to authenticate API requests and log request info
@app.before_request
def authenticate_and_log():
    if request.path.startswith('/api') and request.path != '/api/status':
        auth_header = request.headers.get('Authorization')
        if not auth_header or auth_header != f'Bearer {PASSWORD}':
            app.logger.warning(f"Unauthorized access attempt. Expected: Bearer {PASSWORD}, Got: {auth_header}")
            return jsonify({'error': 'Unauthorized'}), 401
    app.logger.info(f"Request: {request.method} {request.path}")

# New function to fetch ISO list
@app.route('/api/iso', methods=['GET'])
@rate_limited
def get_iso_list():
    try:
        url = f"{PROXMOX_URL}/nodes/{NODE_NAME}/storage/local/content"
        ticket, csrf_token = get_proxmox_ticket()
        headers = {
            'CSRFPreventionToken': csrf_token,
            'Cookie': f'PVEAuthCookie={ticket}'
        }
        response = requests.get(url, headers=headers, verify=VERIFY_SSL)
#        response = requests.get(url, verify=VERIFY_SSL)
        response.raise_for_status()
        iso_list = [iso['volid'] for iso in response.json()['data'] if iso['content'] == 'iso']
        app.logger.debug(f"Fetched ISO list: {iso_list}")
        return jsonify(iso_list)
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error fetching ISO list: {e}")
        return jsonify({'error': 'Failed to fetch ISO list'}), 500

@app.route('/api/status', methods=['GET'])
@rate_limited
def status():
    app.logger.info("Status check")
    return jsonify({'status': 'API is running'})

@app.route('/api/create-vm', methods=['POST'])
@rate_limited
def handle_create_vm():
    vm_data = request.json
    app.logger.info(f"Create VM request with data: {vm_data}")
    return create_vm(vm_data['name'], vm_data['iso'], 'basic')

def can_create_vm(vm_memory_gb, vm_cpu_threads):
    try:
        ticket, csrf_token = get_proxmox_ticket()
        headers = {
            'CSRFPreventionToken': csrf_token,
            'Cookie': f'PVEAuthCookie={ticket}'
        }
        url = f"{PROXMOX_URL}/nodes/{NODE_NAME}/qemu"
        response = requests.get(url, headers=headers, verify=VERIFY_SSL)
        response.raise_for_status()
        vms = response.json()['data']

        # Get the total used resources
        total_used_memory = 0
        total_used_cpu = 0

        for vm in vms:
            total_used_memory += vm['maxmem'] / (1024**3)  # Convert from bytes to GB
            total_used_cpu += vm['maxcpu']

        available_memory = TOTAL_MEMORY_GB - total_used_memory - PROXMOX_MEMORY_OVERHEAD_GB
        available_cpu = TOTAL_CPU_THREADS - total_used_cpu - PROXMOX_CPU_OVERHEAD_THREADS

        if vm_memory_gb > available_memory:
            app.logger.info("Not enough available memory.")
            return False, "Not enough available memory"

        if vm_cpu_threads > available_cpu:
            app.logger.info("Not enough available CPU.")
            return False, "Not enough available CPU"

        return True, "Sufficient resources available"
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error checking resources for VM creation: {e}")
        return False, str(e)

def create_vm(name, iso, tier):
    # Define configurations for different tiers
    tier_configurations = {
        'basic': {'cores': 1, 'memory': 1024, 'storage': 20},
        'standard': {'cores': 2, 'memory': 4096, 'storage': 50},
        'performance': {'cores': 3, 'memory': 6144, 'storage': 100}
    }

    try:
        ticket, csrf_token = get_proxmox_ticket()
        headers = {
            'CSRFPreventionToken': csrf_token,
            'Cookie': f'PVEAuthCookie={ticket}'
        }
        node = NODE_NAME
        url = f"{PROXMOX_URL}/nodes/{node}/qemu"

        # Generate VM ID dynamically by finding the highest existing ID and incrementing it
        existing_vms = get_existing_vms(node)
        highest_id = max(existing_vms) if existing_vms else 101  # Start with 101 if no existing VMs
        vmid = highest_id + 1

        # Get configuration for the specified tier
        tier_config = tier_configurations.get(tier.lower())
        if not tier_config:
            return jsonify({'error': 'Invalid tier'})

        # Check if there are enough resources to create the VM
        can_create, message = can_create_vm(tier_config['memory'] / 1024, tier_config['cores'])
        if not can_create:
            return jsonify({'error': message}), 400

        params = {
            'vmid': vmid,
            'name': name,
            'ide2': f'local:iso/{iso},media=cdrom',
            'sockets': 1,
            'cores': tier_config['cores'],
            'memory': tier_config['memory'],
            'net0': 'e1000,bridge=vmbr1'
        }

        app.logger.debug(f"Sending request to Proxmox: {url} with params: {params}")
        response = requests.post(url, headers=headers, json=params, verify=VERIFY_SSL)
        response.raise_for_status()

        # Set VM to start on boot
        vm_settings(node, vmid)

        app.logger.debug(f"Proxmox response: {response.status_code}, {response.text}")
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error creating VM: {e}")
        return jsonify({'error': str(e)}), 500

# Function to set VM to start on boot
def vm_settings(node, vmid):
    try:
        ticket, csrf_token = get_proxmox_ticket()
        headers = {
            'CSRFPreventionToken': csrf_token,
            'Cookie': f'PVEAuthCookie={ticket}'
        }
        url = f"{PROXMOX_URL}/nodes/{node}/qemu/{vmid}/config"
        params = {'onboot': 1,
                  'autostart': 1,
                  
                 }
        response = requests.put(url, headers=headers, json=params, verify=VERIFY_SSL)
        response.raise_for_status()
        app.logger.info(f"Set VM {vmid} to start on boot.")
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error setting start on boot for VM {vmid} on node {node}: {e}")

# Function to get existing VMs on the node
def get_existing_vms(node):
    try:
        ticket, csrf_token = get_proxmox_ticket()
        headers = {
            'CSRFPreventionToken': csrf_token,
            'Cookie': f'PVEAuthCookie={ticket}'
        }
        url = f"{PROXMOX_URL}/nodes/{node}/qemu"
        response = requests.get(url, headers=headers, verify=VERIFY_SSL)
        response.raise_for_status()
        vms = response.json()['data']
        existing_ids = [int(vm['vmid']) for vm in vms]
        return existing_ids
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error fetching VMs on node {node}: {e}")
        return []

# Route for listing nodes
@app.route('/api/nodes', methods=['GET'])
@rate_limited
def get_nodes():
    try:
        ticket, csrf_token = get_proxmox_ticket()
        headers = {
            'CSRFPreventionToken': csrf_token,
            'Cookie': f'PVEAuthCookie={ticket}'
        }
        url = f"{PROXMOX_URL}/nodes"
        response = requests.get(url, headers=headers, verify=VERIFY_SSL)
        response.raise_for_status()
        nodes = response.json()['data']
        app.logger.debug(f"Fetched nodes: {nodes}")
        return jsonify(nodes)
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error fetching nodes: {e}")
        return jsonify({'error': 'Failed to fetch nodes'}), 500

# Route for listing VMs on a node
@app.route('/api/nodes/<node>/qemu', methods=['GET'])
@rate_limited
def get_vms(node):
    try:
        ticket, csrf_token = get_proxmox_ticket()
        headers = {
            'CSRFPreventionToken': csrf_token,
            'Cookie': f'PVEAuthCookie={ticket}'
        }
        url = f"{PROXMOX_URL}/nodes/{node}/qemu"
        response = requests.get(url, headers=headers, verify=VERIFY_SSL)
        response.raise_for_status()
        vms = response.json()['data']
        app.logger.debug(f"Fetched VMs for node {node}: {vms}")
        return jsonify(vms)
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error fetching VMs on node {node}: {e}")
        return jsonify({'error': f'Failed to fetch VMs on node {node}'}), 500

@app.route('/api/nodes/<node>/qemu/<vmid>/status', methods=['GET'])
@rate_limited
def get_vm_status(node, vmid):
    try:
        ticket, csrf_token = get_proxmox_ticket()
        headers = {
            'CSRFPreventionToken': csrf_token,
            'Cookie': f'PVEAuthCookie={ticket}'
        }
        url = f"{PROXMOX_URL}/nodes/{node}/qemu/{vmid}/status/current"
        response = requests.get(url, headers=headers, verify=VERIFY_SSL)
        response.raise_for_status()
        status = response.json()['data']
        app.logger.debug(f"Fetched status for VM {vmid} on node {node}: {status}")
        return jsonify(status)
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error fetching status for VM {vmid} on node {node}: {e}")
        return jsonify({'error': f'Failed to fetch status for VM {vmid} on node {node}'}), 500

@app.route('/api/nodes/<node>/qemu/<vmid>/config', methods=['POST'])
@rate_limited
def update_vm_config(node, vmid):
    config_data = request.json
    app.logger.info(f"Update config for VM {vmid} on node {node} with data: {config_data}")
    try:
        ticket, csrf_token = get_proxmox_ticket()
        headers = {
            'CSRFPreventionToken': csrf_token,
            'Cookie': f'PVEAuthCookie={ticket}'
        }
        url = f"{PROXMOX_URL}/nodes/{node}/qemu/{vmid}/config"
        response = requests.put(url, headers=headers, json=config_data, verify=VERIFY_SSL)
        response.raise_for_status()
        app.logger.debug(f"Updated config for VM {vmid} on node {node}: {response.json()}")
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error updating config for VM {vmid} on node {node}: {e}")
        return jsonify({'error': f'Failed to update config for VM {vmid} on node {node}'}), 500

# Route for starting a VM
@app.route('/api/nodes/<node>/qemu/<vmid>/status/start', methods=['POST'])
@rate_limited
def start_vm(node, vmid):
    app.logger.info(f"Start VM {vmid} on node {node}")
    try:
        ticket, csrf_token = get_proxmox_ticket()
        headers = {
            'CSRFPreventionToken': csrf_token,
            'Cookie': f'PVEAuthCookie={ticket}'
        }
        url = f"{PROXMOX_URL}/nodes/{node}/qemu/{vmid}/status/start"
        response = requests.post(url, headers=headers, verify=VERIFY_SSL)
        response.raise_for_status()
        app.logger.debug(f"Started VM {vmid} on node {node}")
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error starting VM {vmid} on node {node}: {e}")
        return jsonify({'error': f'Failed to start VM {vmid} on node {node}'}), 500

# Route for stopping a VM
@app.route('/api/nodes/<node>/qemu/<vmid>/status/stop', methods=['POST'])
@rate_limited
def stop_vm(node, vmid):
    try:
        ticket, csrf_token = get_proxmox_ticket()
        headers = {
            'CSRFPreventionToken': csrf_token,
            'Cookie': f'PVEAuthCookie={ticket}'
        }
        url = f"{PROXMOX_URL}/nodes/{node}/qemu/{vmid}/status/stop"
        response = requests.post(url, headers=headers, verify=VERIFY_SSL)
        response.raise_for_status()
        app.logger.info(f"Stopped VM {vmid} on node {node}")
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error stopping VM {vmid} on node {node}: {e}")
        return jsonify({'error': f'Failed to stop VM {vmid} on node {node}'}), 500

# Route for deleting a VM
@app.route('/api/nodes/<node>/qemu/<vmid>', methods=['DELETE'])
@rate_limited
def delete_vm(node, vmid):
    try:
        ticket, csrf_token = get_proxmox_ticket()
        headers = {
            'CSRFPreventionToken': csrf_token,
            'Cookie': f'PVEAuthCookie={ticket}'
        }
        url = f"{PROXMOX_URL}/nodes/{node}/qemu/{vmid}"
        response = requests.delete(url, headers=headers, verify=VERIFY_SSL)
        response.raise_for_status()
        app.logger.info(f"Deleted VM {vmid} on node {node}")
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error deleting VM {vmid} on node {node}: {e}")
        return jsonify({'error': f'Failed to delete VM {vmid} on node {node}'}), 500

##########################################################################################################

#                                   --- CHECKS BEGIN HERE ---

##########################################################################################################

# Function to check Proxmox connection
def check_proxmox_connection(ticket, csrf_token):
    app.logger.info("Checking Proxmox connection...")
    try:
        url = f"{PROXMOX_URL}/nodes"
        headers = {
            'CSRFPreventionToken': csrf_token,
            'Cookie': f'PVEAuthCookie={ticket}'
        }
        response = requests.get(url, headers=headers, verify=VERIFY_SSL)
        response.raise_for_status()
        app.logger.info(f"Proxmox connection response: {json.dumps(response.json(), indent=2)}")
        return True
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error checking Proxmox connection: {e}")
        return False

# Function to check ISO fetch
def check_iso_fetch(ticket, csrf_token):
    app.logger.info("Checking ISO fetch...")
    try:
        url = f"{PROXMOX_URL}/nodes/{NODE_NAME}/storage/local/content"
        headers = {
            'CSRFPreventionToken': csrf_token,
            'Cookie': f'PVEAuthCookie={ticket}'
        }
        response = requests.get(url, headers=headers, verify=VERIFY_SSL)
        response.raise_for_status()
        app.logger.info(f"ISO fetch response: {json.dumps(response.json(), indent=2)}")
        return True
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error fetching ISOs: {e}")
        return False

# Function to check VM creation
def check_vm_create(ticket, csrf_token):
    app.logger.info("Checking VM creation...")
    try:
        url = f"{PROXMOX_URL}/nodes/{NODE_NAME}/qemu"
        headers = {
            'CSRFPreventionToken': csrf_token,
            'Cookie': f'PVEAuthCookie={ticket}'
        }
        response = requests.get(url, headers=headers, verify=VERIFY_SSL)
        response.raise_for_status()
        app.logger.info(f"VM creation response: {json.dumps(response.json(), indent=2)}")
        return True
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error checking VM creation: {e}")
        return False

# Function to perform pre-checks before starting Flask server
def perform_pre_checks():
    app.logger.info("Performing pre-checks...")
    try:
        ticket, csrf_token = get_proxmox_ticket()
        if not check_proxmox_connection(ticket, csrf_token) or not check_iso_fetch(ticket, csrf_token) or not check_vm_create(ticket, csrf_token):
            response = input("Pre-checks failed. Do you want to continue loading the Flask server? (y/n): ")
            if response.lower() != 'y':
                app.logger.info("Exiting.")
                return False
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Pre-checks could not be performed due to an error: {e}")
        return False
    return True

# Function to dump all API endpoint responses
def dump_all_endpoints():
    app.logger.info("Dumping all API endpoint responses...")
    endpoints = [rule.rule for rule in app.url_map.iter_rules() if rule.rule.startswith('/api') and 'GET' in rule.methods]
    responses = {}
    with app.test_client() as client:
        for endpoint in endpoints:
            if endpoint != '/api/status':
                response = client.get(endpoint, headers={'Authorization': f'Bearer {PASSWORD}'})
                try:
                    responses[endpoint] = response.get_json()
                except Exception as e:
                    responses[endpoint] = {'error': str(e)}
    with open('api_dump.json', 'w') as f:
        json.dump(responses, f, indent=2)
    app.logger.info("API responses dumped successfully.")

# Main function to start Flask server
def main():
    if not perform_pre_checks():
        return
    app.logger.info("Starting Flask server...")
    app.run(host='0.0.0.0', port=8080, debug=True)

if __name__ == "__main__":
    main()
