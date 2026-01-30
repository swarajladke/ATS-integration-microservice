# Zoho Recruit OAuth Setup Guide

To integrate with Zoho Recruit, you need to set up OAuth 2.0 credentials. Follow these steps:

## 1. Get Client ID and Client Secret

1. Go to the **Zoho API Console**: [api-console.zoho.in](https://api-console.zoho.in/) (for India region).
2. Click **Add Client**.
3. Choose **Server-based Applications**.
4. Fill in the details:
   - **Client Name**: ATS Integration Microservice
   - **Homepage URL**: `http://localhost:3000`
   - **Authorized Redirect URIs**: `http://localhost:3000/callback`
5. Click **Create**.
6. Copy your **Client ID** and **Client Secret**.

## 2. Generate Authorization Code (The "Self-Client" Method)

1. In the same API Console, click on your created client.
2. Go to the **Self Client** tab.
3. In the **Scope** field, enter exactly this:
   `ZohoRecruit.modules.ALL,ZohoRecruit.settings.modules.ALL`
4. Set **Time Duration** to 10 minutes.
5. Click **Create**.
6. Select your **Portal** (if asked) and click **Authorize**.
7. Copy the generated **Code**. This is your **Authorization Code**.

## 3. Get the Refresh Token

You need to exchange the Authorization Code for a Permanent Refresh Token. You can do this with a simple `curl` command in your terminal:

```bash
curl -X POST "https://accounts.zoho.in/oauth/v2/token" \
-d "code=YOUR_AUTHORIZATION_CODE" \
-d "client_id=YOUR_CLIENT_ID" \
-d "client_secret=YOUR_CLIENT_SECRET" \
-d "grant_type=authorization_code"
```

**Note**: Replace the placeholders. If you are using Windows PowerShell, use backticks `` ` `` instead of backslashes `\` for line breaks.

The JSON response will contain:
- `access_token` (Short lived)
- `refresh_token` (**THIS IS WHAT YOU NEED**)
- `api_domain` (Confirm it matches `https://recruit.zoho.in`)

## 4. Update your .env file

Add these to your `.env` file in the project root:

```env
ATS_PROVIDER=zoho_recruit
ZOHO_CLIENT_ID=your_client_id
ZOHO_CLIENT_SECRET=your_client_secret
ZOHO_REFRESH_TOKEN=your_refresh_token
ZOHO_REGION=in
```
