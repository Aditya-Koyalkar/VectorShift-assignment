# slack.py

import json
import secrets
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import httpx
import asyncio
import base64
import requests
from integrations.integration_item import IntegrationItem
from typing import List
from datetime import datetime
from dateutil.parser import parse as parse_datetime  # Add this import

from redis_client import add_key_value_redis, get_value_redis, delete_key_redis

# Replace these with your HubSpot app credentials
CLIENT_ID = 'e5edfa88-8462-42cd-a169-3f7113c33c77'
CLIENT_SECRET = 'bcb9c9e2-a8a3-4e27-8d7c-d1eaaebe6670'
encoded_client_id_secret = base64.b64encode(f'{CLIENT_ID}:{CLIENT_SECRET}'.encode()).decode()

REDIRECT_URI = 'http://localhost:8000/integrations/hubspot/oauth2callback'
SCOPES = 'oauth%20crm.objects.contacts.read'
authorization_url = f'https://app.hubspot.com/oauth/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope={SCOPES}'

async def authorize_hubspot(user_id, org_id):
    state_data = {
        'state': secrets.token_urlsafe(32),
        'user_id': user_id,
        'org_id': org_id
    }
    encoded_state = json.dumps(state_data)
    await add_key_value_redis(f'hubspot_state:{org_id}:{user_id}', encoded_state, expire=600)

    return f'{authorization_url}&state={encoded_state}'

async def oauth2callback_hubspot(request: Request):
    if request.query_params.get('error'):
        raise HTTPException(status_code=400, detail=request.query_params.get('error'))
    
    code = request.query_params.get('code')
    encoded_state = request.query_params.get('state')
    state_data = json.loads(encoded_state)

    original_state = state_data.get('state')
    user_id = state_data.get('user_id')
    org_id = state_data.get('org_id')
    saved_state = await get_value_redis(f'hubspot_state:{org_id}:{user_id}')
    if not saved_state or original_state != json.loads(saved_state).get('state'):
        raise HTTPException(status_code=400, detail='State does not match.')

    async with httpx.AsyncClient() as client:
        response, _ = await asyncio.gather(
            client.post(
                'https://api.hubapi.com/oauth/v1/token',
                data={
                    'grant_type': 'authorization_code',
                    'client_id': CLIENT_ID,
                    'client_secret': CLIENT_SECRET,
                    'redirect_uri': REDIRECT_URI,
                    'code': code
                },
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            ),
            delete_key_redis(f'hubspot_state:{org_id}:{user_id}'),
        )

    await add_key_value_redis(f'hubspot_credentials:{org_id}:{user_id}', json.dumps(response.json()), expire=600)
    
    close_window_script = """
    <html>
        <script>
            window.close();
        </script>
    </html>
    """
    return HTMLResponse(content=close_window_script)

async def get_hubspot_credentials(user_id, org_id):
    credentials = await get_value_redis(f'hubspot_credentials:{org_id}:{user_id}')
    if not credentials:
        raise HTTPException(status_code=400, detail='No credentials found.')
    credentials = json.loads(credentials)
    if not credentials:
        raise HTTPException(status_code=400, detail='No credentials found.')
    await delete_key_redis(f'hubspot_credentials:{org_id}:{user_id}')

    return credentials

def create_integration_item_from_contact(contact):
    """Creates an IntegrationItem from a HubSpot contact"""
    created_at = contact.get('createdAt')
    updated_at = contact.get('updatedAt')

    return IntegrationItem(
        id=contact.get('id'),
        type='contact',
        name=f"{contact.get('properties', {}).get('firstname', '')} {contact.get('properties', {}).get('lastname', '')}".strip(),
        creation_time=parse_datetime(created_at) if created_at else None,
        last_modified_time=parse_datetime(updated_at) if updated_at else None,
        url=f"https://app.hubspot.com/contacts/{contact.get('id')}",
        visibility=True
    )

async def get_items_hubspot(credentials) -> List[IntegrationItem]:
    """Retrieves contacts from HubSpot and converts them to IntegrationItems"""
    credentials = json.loads(credentials)
    access_token = credentials.get('access_token')
    
    if not access_token:
        raise HTTPException(status_code=400, detail='Invalid credentials')

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    # Get contacts from HubSpot
    response = requests.get(
        'https://api.hubapi.com/crm/v3/objects/contacts',
        headers=headers,
        params={'limit': 100}  # Adjust limit as needed
    )

    if response.status_code == 200:
        contacts = response.json().get('results', [])
        integration_items = [create_integration_item_from_contact(contact) for contact in contacts]
        print(integration_items)  # Print for debugging
        return integration_items
    
    return []