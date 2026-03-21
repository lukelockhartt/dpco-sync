"""
One-time script to get a Plaid access token via the Link flow.
Run this, open http://localhost:8080 in your browser, connect your bank,
and the access token will be written to your .env file automatically.
"""

import os
import re
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv

import plaid
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.products import Products
from plaid.model.country_code import CountryCode

load_dotenv()

PORT = 8443
OAUTH_REDIRECT_URI = f"https://localhost:{PORT}/oauth-callback"

app = Flask(__name__)


def get_client() -> plaid_api.PlaidApi:
    configuration = plaid.Configuration(
        host=plaid.Environment.Production,
        api_key={
            "clientId": os.environ["PLAID_CLIENT_ID"],
            "secret": os.environ["PLAID_SECRET"],
        },
    )
    return plaid_api.PlaidApi(plaid.ApiClient(configuration))


@app.route("/")
def index():
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Connect Bank</title>
  <script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"></script>
  <style>
    body { font-family: system-ui, sans-serif; display: flex; justify-content: center;
           align-items: center; height: 100vh; margin: 0; background: #f5f5f5; }
    .card { background: white; padding: 2rem 3rem; border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,.1); text-align: center; max-width: 400px; }
    h1 { font-size: 1.4rem; margin-bottom: .5rem; }
    p  { color: #666; margin-bottom: 1.5rem; }
    button { background: #2563eb; color: white; border: none; padding: .75rem 2rem;
             border-radius: 8px; font-size: 1rem; cursor: pointer; }
    button:hover { background: #1d4ed8; }
    #status { margin-top: 1rem; color: #16a34a; font-weight: 600; min-height: 1.5rem; }
  </style>
</head>
<body>
<div class="card">
  <h1>Connect Your Bank</h1>
  <p>One-time setup to link your Dupaco account and get your access token.</p>
  <button id="btn">Connect Bank Account</button>
  <div id="status"></div>
</div>
<script>
  const status = document.getElementById('status');

  async function initLink(token, receivedRedirectUri) {
    const config = {
      token,
      onSuccess: async (publicToken) => {
        status.textContent = 'Saving your access token...';
        const res = await fetch('/exchange_token', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ public_token: publicToken }),
        });
        const data = await res.json();
        if (data.success) {
          status.textContent = '✓ Access token saved to .env! You can close this tab.';
          document.getElementById('btn').disabled = true;
        } else {
          status.textContent = 'Error: ' + (data.error || 'unknown');
        }
      },
      onExit: (err) => {
        if (err) status.textContent = 'Error: ' + err.error_message;
      },
    };
    if (receivedRedirectUri) config.receivedRedirectUri = receivedRedirectUri;
    const handler = Plaid.create(config);
    handler.open();
  }

  // Check if we're returning from an OAuth redirect
  const params = new URLSearchParams(window.location.search);
  if (params.has('oauth_state_id')) {
    fetch('/create_link_token', { method: 'POST' })
      .then(r => r.json())
      .then(d => initLink(d.link_token, window.location.href));
  }

  document.getElementById('btn').addEventListener('click', async () => {
    status.textContent = 'Loading...';
    const res = await fetch('/create_link_token', { method: 'POST' });
    const data = await res.json();
    if (data.link_token) {
      initLink(data.link_token, null);
    } else {
      status.textContent = 'Error creating link token: ' + JSON.stringify(data);
    }
  });
</script>
</body>
</html>"""


@app.route("/oauth-callback")
def oauth_callback():
    """Plaid redirects here after OAuth bank login."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>Completing connection...</title>
  <script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"></script>
  <style>
    body { font-family: system-ui, sans-serif; display: flex; justify-content: center;
           align-items: center; height: 100vh; margin: 0; background: #f5f5f5; }
    .card { background: white; padding: 2rem 3rem; border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,.1); text-align: center; }
    #status { font-size: 1.1rem; color: #2563eb; }
  </style>
</head>
<body>
<div class="card">
  <div id="status">Completing bank connection...</div>
</div>
<script>
  const status = document.getElementById('status');

  fetch('/create_link_token', { method: 'POST' })
    .then(r => r.json())
    .then(data => {
      const handler = Plaid.create({
        token: data.link_token,
        receivedRedirectUri: window.location.href,
        onSuccess: async (publicToken) => {
          status.textContent = 'Saving access token...';
          const res = await fetch('/exchange_token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ public_token: publicToken }),
          });
          const result = await res.json();
          if (result.success) {
            status.textContent = '✓ Done! Access token saved. You can close this tab.';
          } else {
            status.textContent = 'Error: ' + (result.error || 'unknown');
          }
        },
        onExit: (err) => {
          if (err) status.textContent = 'Error: ' + err.error_message;
        },
      });
      handler.open();
    });
</script>
</body>
</html>"""


@app.route("/create_link_token", methods=["POST"])
def create_link_token():
    try:
        client = get_client()
        request_obj = LinkTokenCreateRequest(
            user=LinkTokenCreateRequestUser(client_user_id="local-user"),
            client_name="My Finance App",
            products=[Products("transactions")],
            country_codes=[CountryCode("US")],
            language="en",
            redirect_uri=OAUTH_REDIRECT_URI,
        )
        response = client.link_token_create(request_obj)
        return jsonify({"link_token": response["link_token"]})
    except plaid.ApiException as e:
        return jsonify({"error": str(e)}), 400


@app.route("/exchange_token", methods=["POST"])
def exchange_token():
    try:
        public_token = request.json["public_token"]
        client = get_client()
        exchange_request = ItemPublicTokenExchangeRequest(public_token=public_token)
        response = client.item_public_token_exchange(exchange_request)
        access_token = response["access_token"]

        # Write access token to .env
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        with open(env_path, "r") as f:
            content = f.read()

        if "PLAID_ACCESS_TOKEN=" in content:
            content = re.sub(r"PLAID_ACCESS_TOKEN=.*", f"PLAID_ACCESS_TOKEN={access_token}", content)
        else:
            content += f"\nPLAID_ACCESS_TOKEN={access_token}\n"

        with open(env_path, "w") as f:
            f.write(content)

        print(f"\n✓ Access token saved: {access_token}\n")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


if __name__ == "__main__":
    print(f"\nOpen https://localhost:{PORT} in your browser.")
    print("You will see a security warning — click 'Advanced' then 'Proceed to localhost' to continue.\n")
    app.run(port=PORT, ssl_context="adhoc")
