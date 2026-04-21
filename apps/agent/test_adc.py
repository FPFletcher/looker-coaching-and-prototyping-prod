import google.auth
try:
    credentials, project = google.auth.default()
    print("Type:", type(credentials))
    from google.oauth2 import service_account
    if isinstance(credentials, service_account.Credentials):
        print("SA Email:", credentials.service_account_email)
except Exception as e:
    print("Error:", e)
