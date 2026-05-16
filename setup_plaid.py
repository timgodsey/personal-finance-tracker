import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv, set_key
import plaid
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest

load_dotenv()

app = FastAPI()

PLAID_CLIENT_ID = os.getenv('PLAID_CLIENT_ID')
PLAID_SECRET = os.getenv('PLAID_SECRET')
PLAID_ENV = os.getenv('PLAID_ENV', 'sandbox')

if PLAID_ENV == 'sandbox':
    host = plaid.Environment.Sandbox
elif PLAID_ENV == 'development':
    host = plaid.Environment.Development
else:
    host = plaid.Environment.Production

configuration = plaid.Configuration(
    host=host,
    api_key={
        'clientId': PLAID_CLIENT_ID,
        'secret': PLAID_SECRET,
    }
)
api_client = plaid.ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)

class PublicTokenRequest(BaseModel):
    public_token: str

@app.get("/")
def index():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Plaid Link</title>
        <script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"></script>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 flex items-center justify-center h-screen">
        <div class="bg-white p-8 rounded shadow-md text-center max-w-md w-full">
            <h1 class="text-2xl font-bold mb-6">Connect Your Bank</h1>
            <p class="mb-6 text-gray-600">Link your bank account using Plaid to fetch financial data securely.</p>
            <button id="link-button" class="bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold w-full hover:bg-blue-700 transition">Link Account</button>
            <div id="status" class="mt-4 text-sm font-medium"></div>
        </div>

        <script>
            document.addEventListener('DOMContentLoaded', async () => {
                try {
                    const fetchTokenResponse = await fetch('/create_link_token');
                    if (!fetchTokenResponse.ok) {
                        const errorText = await fetchTokenResponse.text();
                        console.error(errorText);
                        document.getElementById('status').innerText = 'Backend Error: ' + errorText;
                        document.getElementById('status').classList.add('text-red-600');
                        return;
                    }
                    const data = await fetchTokenResponse.json();
                    const link_token = data.link_token;

                const handler = Plaid.create({
                    token: link_token,
                    onSuccess: async (public_token, metadata) => {
                        document.getElementById('status').innerText = 'Exchanging token...';
                        document.getElementById('status').classList.add('text-blue-600');
                        
                        const response = await fetch('/exchange_public_token', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ public_token: public_token })
                        });
                        
                        if (response.ok) {
                            document.getElementById('status').innerText = 'Success! Access token saved. You can close this window and stop the server.';
                            document.getElementById('status').classList.remove('text-blue-600');
                            document.getElementById('status').classList.add('text-green-600');
                        } else {
                            document.getElementById('status').innerText = 'Failed to exchange token.';
                            document.getElementById('status').classList.add('text-red-600');
                        }
                    },
                    onLoad: () => {},
                    onExit: (err, metadata) => {
                        if (err != null) {
                            console.error('Plaid Link exit error:', err);
                        }
                    },
                    onEvent: (eventName, metadata) => {}
                });

                document.getElementById('link-button').onclick = function() {
                    handler.open();
                };
                } catch (e) {
                    console.error(e);
                    document.getElementById('status').innerText = 'Frontend Error: ' + e.message;
                    document.getElementById('status').classList.add('text-red-600');
                }
            });
        </script>
    </body>
    </html>
    """)

@app.get("/create_link_token")
def create_link_token():
    try:
        request = LinkTokenCreateRequest(
            products=[Products("transactions")],
            client_name="Finance AI",
            country_codes=[CountryCode("CA")],
            language="en",
            user=LinkTokenCreateRequestUser(
                client_user_id="user-123"
            )
        )
        response = client.link_token_create(request)
        return response.to_dict()
    except plaid.ApiException as e:
        from fastapi import HTTPException
        import json
        try:
            detail = json.loads(e.body)
        except:
            detail = str(e.body)
        raise HTTPException(status_code=400, detail=detail)

@app.post("/exchange_public_token")
def exchange_public_token(request: PublicTokenRequest):
    exchange_request = ItemPublicTokenExchangeRequest(
        public_token=request.public_token
    )
    exchange_response = client.item_public_token_exchange(exchange_request)
    access_token = exchange_response['access_token']
    
    # Save to .env
    set_key('.env', 'PLAID_ACCESS_TOKEN', access_token)
    
    return {"status": "success"}

if __name__ == "__main__":
    print("🚀 Starting Plaid Setup Server. Go to http://localhost:8000 to link your bank.")
    uvicorn.run(app, host="127.0.0.1", port=8000)
