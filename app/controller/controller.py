import requests

def fetch_gmail_messages(access_token: str):
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Step 1: Get list of messages
    list_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
    list_resp = requests.get(list_url, headers=headers)
    list_resp.raise_for_status()
    messages = list_resp.json().get("messages", [])
    
    emails = []
    
    # Step 2: For each message, fetch full data
    for msg in messages[:5]:  # limit to first 5 for testing
        msg_id = msg["id"]
        detail_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}"
        detail_resp = requests.get(detail_url, headers=headers, params={"format": "full"})
        detail_resp.raise_for_status()
        msg_data = detail_resp.json()
        
        # Extract subject, from, body
        headers_list = msg_data["payload"].get("headers", [])
        subject = next((h["value"] for h in headers_list if h["name"] == "Subject"), "")
        sender = next((h["value"] for h in headers_list if h["name"] == "From"), "")
        
        # Body may be base64 encoded
        body = ""
        if "parts" in msg_data["payload"]:
            for part in msg_data["payload"]["parts"]:
                if part["mimeType"] == "text/plain":
                    body = part["body"].get("data", "")
                    break
        else:
            body = msg_data["payload"]["body"].get("data", "")
        
        if body:
            import base64
            body = base64.urlsafe_b64decode(body).decode("utf-8", errors="ignore")
        
        emails.append({
            "id": msg_id,
            "from": sender,
            "subject": subject,
            "body": body.strip()
        })
    
    return emails
