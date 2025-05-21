import requests
import os
from dotenv import load_dotenv

load_dotenv()

# --- Replace with your actual credentials and desired scopes ---
FILEVINE_IDENTITY_URL = "https://identity.filevine.com/connect/token"
PAT = "YOUR_PERSONAL_ACCESS_TOKEN_HERE"
CLIENT_ID = "YOUR_CLIENT_ID_HERE" # e.g., "0WqoIIVqN2Z40mc@filevine.api"
CLIENT_SECRET = 
SCOPES = "filevine" # Or "fv.api" or other specific scopes

def get_org_with_token():
    url = "https://api.filevineapp.ca/fv-app/v2/utils/GetUserOrgsWithToken"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": "123"
    }

    response = requests.post(url, headers=headers)

    return response.json()

def authenticate_client(id_url:str=FILEVINE_IDENTITY_URL, pat:str=PAT, 
                        client_id:str=CLIENT_ID, client_secret:str=CLIENT_SECRET, scopes:str=SCOPES):
    payload = {
        'grant_type': 'personal_access_token',
        'token': PAT,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'scope': SCOPES
    }

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    print("Attempting to get Bearer token...")
    
    try:
        response = requests.post(FILEVINE_IDENTITY_URL, data=payload, headers=headers)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)

        token_data = response.json()
        bearer_token = token_data.get('access_token')
        expires_in = token_data.get('expires_in')
        token_type = token_data.get('token_type')

        if bearer_token:
            print(f"Successfully obtained Bearer Token!")
            print(f"Token Type: {token_type}")
            print(f"Access Token: {bearer_token}") # Be careful about logging this in real applications
            print(f"Expires In (seconds): {expires_in}")
        else:
            print("Error: 'access_token' not found in the response.")
            print("Full response:", token_data)

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        print(f"Response status code: {response.status_code}")
        try:
            print(f"Response content: {response.json()}")
        except ValueError:
            print(f"Response content: {response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"Request error occurred: {req_err}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")



