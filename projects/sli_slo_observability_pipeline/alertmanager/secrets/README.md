# Alertmanager secrets

Put your Gmail App Password in a file here named `gmail_app_password` (no
extension, no trailing newline). It's gitignored — never commit it.

```bash
echo -n "your16charapppassword" > gmail_app_password
docker compose restart alertmanager
```

## Creating the App Password

1. Requires 2-Step Verification enabled on the Google account.
2. https://myaccount.google.com/apppasswords → create one, name it
   "sli-slo-alertmanager" or similar → copy the 16-character password.
3. Save it into `gmail_app_password` as above. Regular account passwords do
   NOT work here — Gmail blocks plain-password SMTP auth; only App Passwords
   are accepted.

## Also required

Edit `../alertmanager.yml` and replace the two placeholder addresses
(`smtp_from`/`smtp_auth_username`, and the `to:` under `receivers`) with
real ones — they're plain email addresses, low-sensitivity, tracked in git
by design so the config is self-documenting. Only the password itself stays
out of git.
