import requests
import json

data = {
    "code": "1000.02360411dcb0a63e8b2f970509e8b128.4da22a2bdda125b882450f2ce4044ed4",
    "client_id": "1000.WKM4N1VZ6RFFY69N79C2JJU3QSCDYZ",
    "client_secret": "c3e7e4a2413a2cfa4570acfea196ad5d9ab85975b0",
    "grant_type": "authorization_code"
}

response = requests.post("https://accounts.zoho.in/oauth/v2/token", data=data)
print(json.dumps(response.json(), indent=2))
