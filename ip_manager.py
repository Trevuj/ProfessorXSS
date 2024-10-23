import os
import json
import requests
import base64
from datetime import datetime, timedelta

# Constants
GITHUB_TOKEN = "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"  # Set this as an environment variable
GITHUB_REPO_URL = "https://api.github.com/repos/Trevuj/IP_Distribution/contents"
LAST_REQUEST_FILE = "last_request.json"
USERS_FILE = "user_data.json"

# Define IP groups
US_IP_FILES = [
    "us_california_ips.txt",
    "us_florida_ips.txt",
    "us_georgia_ips.txt",
    "us_new_york_ips.txt",
    "us_texas_ips.txt",
]

GLOBAL_IP_FILES = [
    "ca_ips.txt",
    "uk_ips.txt",
]

# Utility Functions
def load_json_from_github(file_name):
    url = f"{GITHUB_REPO_URL}/{file_name}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        content = response.json().get("content")
        if content:
            try:
                # Decode the base64 content
                decoded_content = base64.b64decode(content).decode('utf-8')
                return json.loads(decoded_content)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
                print(f"Response content: {decoded_content}")  # Updated to show the decoded content
    else:
        print(f"Failed to load {file_name}: {response.status_code} {response.text}")
    return {}

def save_json_to_github(filename, data):
    url = f"{GITHUB_REPO_URL}/{filename}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    # Fetch the current content to get the SHA
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        current_content = response.json()
        sha = current_content['sha']
        
        # Prepare data for updating the file
        json_data = json.dumps(data)
        encoded_data = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
        
        # Update the file
        update_response = requests.put(url, headers=headers, json={
            "message": "Updating " + filename,
            "content": encoded_data,
            "sha": sha
        })
        
        if update_response.status_code != 200:
            print(f"Failed to update {filename}: {update_response.status_code} {update_response.text}")
    elif response.status_code == 404:
        # If file doesn't exist, create it
        json_data = json.dumps(data)
        encoded_data = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
        
        create_response = requests.put(url, headers=headers, json={
            "message": "Creating " + filename,
            "content": encoded_data
        })
        
        if create_response.status_code != 201:
            print(f"Failed to create {filename}: {create_response.status_code} {create_response.text}")
    else:
        print(f"Failed to load {filename}: {response.status_code} {response.text}")

def get_user_credentials():
    users = load_json_from_github(USERS_FILE)
    username = input("Enter your username: ")
    password = input("Enter your password: ")

    if username in users and users[username]["password"] == password:
        print(f"Credentials valid for {username}.")
        return username
    print("Invalid credentials.")
    exit()

def can_request_ip(username, ip_file):
    users = load_json_from_github(USERS_FILE)  # Load users to check expiration date
    expiration_date_str = users[username]["expiration_date"]
    
    # Check if the expiration date exists and parse it
    if expiration_date_str:
        expiration_date = datetime.fromisoformat(expiration_date_str)

        # Check if the user's access has expired
        if datetime.now() > expiration_date:
            print(f"Your IP subscription has expired on {expiration_date}.")
            return False  # Return false to indicate that the request cannot be processed

    # If subscription is still valid, check the last request time
    last_requests = load_json_from_github(LAST_REQUEST_FILE)

    # Check for requests to any of the US IP files
    if is_us_ip_request(ip_file) and has_recent_us_ip_request(username):
        print("You must wait 8 hours before requesting another IP from any US state IP file.")
        return False

    # Check the last request time for the specific ip_file
    last_request_time = last_requests.get(username, {}).get(ip_file)
    if last_request_time:
        last_request_time = datetime.fromisoformat(last_request_time)
        if datetime.now() - last_request_time < timedelta(hours=8):
            print("You must wait 8 hours before requesting another IP from this IP file.")
            return False

    return True  # Access is valid and the user can request an IP

def update_last_request_time(username, ip_file):
    last_requests = load_json_from_github(LAST_REQUEST_FILE)
    if username not in last_requests:
        last_requests[username] = {}

    # Log the current time for the specific IP file
    last_requests[username][ip_file] = datetime.now().isoformat()

    save_json_to_github(LAST_REQUEST_FILE, last_requests)

def is_us_ip_request(ip_file):
    return ip_file in US_IP_FILES

def has_recent_us_ip_request(username):
    last_requests = load_json_from_github(LAST_REQUEST_FILE)
    user_requests = last_requests.get(username, {})

    for ip_file in US_IP_FILES:
        if ip_file in user_requests:
            last_request_time = datetime.fromisoformat(user_requests[ip_file])
            if datetime.now() - last_request_time < timedelta(hours=8):
                return True
    return False

def has_recent_global_ip_request(username):
    last_requests = load_json_from_github(LAST_REQUEST_FILE)
    user_requests = last_requests.get(username, {})

    for ip_file in GLOBAL_IP_FILES:
        if ip_file in user_requests:
            last_request_time = datetime.fromisoformat(user_requests[ip_file])
            if datetime.now() - last_request_time < timedelta(hours=8):
                return True
    return False

def get_ip_type():
    print("Choose IP type:")
    ip_types = US_IP_FILES + GLOBAL_IP_FILES

    for index, ip_type in enumerate(ip_types, start=1):
        print(f"{index}. {ip_type}")

    while True:
        try:
            choice = int(input("Choose a number: "))
            if 1 <= choice <= len(ip_types):
                return ip_types[choice - 1]
            else:
                print("Invalid choice. Please select a valid number.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def fetch_ip_file(ip_file):
    url = f"{GITHUB_REPO_URL}/ip_files/{ip_file}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Failed to load IPs from {ip_file}: {response.status_code}")
        return None, []

    content = response.json().get("content")
    if content:
        # Decode the base64 content
        decoded_content = base64.b64decode(content).decode('utf-8')
        ips = decoded_content.splitlines()  # Split lines into a list of IPs
        return ips[0] if ips else None, ips  # Return the first IP and the full list
    return None, []

def save_used_ip(ip, username):
    used_ips = load_json_from_github("used_ip.json")
    if username not in used_ips:
        used_ips[username] = []

    used_ips[username].append({"ip": ip, "timestamp": datetime.now().isoformat()})
    save_json_to_github("used_ip.json", used_ips)

def update_ip_file(ip_file, all_ips, used_ip):
    url = f"{GITHUB_REPO_URL}/ip_files/{ip_file}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    # Check if the file exists to get the current content and sha
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        current_content = response.json()
        sha = current_content['sha']
        
        # Logic to update the file, possibly removing the used IP from all_ips
        updated_ips = [ip for ip in all_ips if ip != used_ip]  # Remove the used IP from the list
        
        # Prepare the new content, with each IP on a new line
        new_content = "\n".join(updated_ips)  # Join the IPs with newline characters
        
        encoded_data = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')
        
        # Update the file
        update_response = requests.put(url, headers=headers, json={
            "message": f"Update {ip_file} after using IP {used_ip}",
            "content": encoded_data,
            "sha": sha
        })
        
        if update_response.status_code != 200:
            print(f"Failed to update {ip_file}: {update_response.status_code} {update_response.text}")
    elif response.status_code == 404:
        print(f"IP file {ip_file} not found.")
    else:
        print(f"Failed to load {ip_file}: {response.status_code} {response.text}")



# Main Execution
if __name__ == "__main__":
    username = get_user_credentials()
    ip_file = get_ip_type()

    if can_request_ip(username, ip_file):
        ip, all_ips = fetch_ip_file(ip_file)
        if ip:
            print(f"Granted IP: {ip}")
            save_used_ip(ip, username)
            update_last_request_time(username, ip_file)
            update_ip_file(ip_file, all_ips, ip)  # Pass the full list and the used IP to update the file
        else:
            print(f"No IPs available in {ip_file}.")
