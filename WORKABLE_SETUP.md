# Workable Setup Guide

This guide will help you obtain the necessary credentials to integrate the ATS Microservice with Workable.

## 1. Create a Workable Account
If you don't have one, sign up for a trial at [workable.com](https://www.workable.com/).

## 2. Get your Subdomain
Your subdomain is the first part of your Workable URL.
Example: If your URL is `https://acme-tools.workable.com`, your subdomain is `acme-tools`.

## 3. Generate an API Key
1. Log in to your Workable account.
2. Click on your profile icon/name in the top-right and select **Settings**.
3. In the left sidebar, under the **Recruiting** section, click on **Integrations**.
4. Scroll down to the **Apps** section.
5. Click **Generate new token**.
6. Give it a name (e.g., "ATS Integration Microservice").
7. **IMPORTANT:** Select the following scopes:
   - `r_jobs` (Read jobs)
   - `r_candidates` (Read candidates)
   - `w_candidates` (Write candidates - required for creating applications)
8. Click **Generate code**.
9. Copy the generated **API Key** immediately (you won't see it again).

## 4. Update your .env file
Add the following to your `.env` file:

```env
ATS_PROVIDER=workable
WORKABLE_API_KEY=your_generated_api_key_here
WORKABLE_SUBDOMAIN=your_subdomain_here
```

## 5. Verify the Integration
Run the following command to check if the integration is working:
```bash
python -c "from src.adapters.factory import get_adapter; a = get_adapter(); print(f'Health Check: {a.health_check()}')"
```
