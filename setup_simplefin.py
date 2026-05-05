import requests
import base64
import os

def claim_token(setup_token):

    # The token is literally just a base64 encoded URL. Decode it:
    try:
        claim_url = base64.b64decode(setup_token).decode('utf-8')
    except Exception as e:
        print(f"Error decoding token: {e}")
        return

    print(f"Claiming token at URL...")
    # Send an empty POST request to the claim URL to get your permanent access credentials
    response = requests.post(claim_url)
    
    if response.status_code == 200:
        access_url = response.text.strip()
        print(f"Success! Access URL obtained.")
        
        # Save to .env file
        env_file = '.env'
        env_lines = []
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                env_lines = f.readlines()
        
        # Remove old URL if it exists
        env_lines = [line for line in env_lines if not line.startswith('SIMPLEFIN_ACCESS_URL=')]
        
        # Ensure the last line has a newline
        if env_lines and not env_lines[-1].endswith('\n'):
            env_lines[-1] += '\n'
            
        env_lines.append(f'SIMPLEFIN_ACCESS_URL={access_url}\n')
        
        with open(env_file, 'w') as f:
            f.writelines(env_lines)
            
        print(f"Access URL saved to .env file as SIMPLEFIN_ACCESS_URL.")
    else:
        print(f"Failed to claim token: {response.status_code} {response.text}")

if __name__ == "__main__":
    print("Welcome to SimpleFIN Setup")
    print("Go to bridge.simplefin.org, link your bank, and generate a Setup Token.")
    token = input("PASTE_YOUR_LONG_BASE64_TOKEN_HERE: ").strip()
    if token:
        claim_token(token)
    else:
        print("No token provided.")
