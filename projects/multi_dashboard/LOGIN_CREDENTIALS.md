# 🔐 Login Credentials

When you access the application at http://localhost:5173, you'll need to log in.

## Default Development Credentials

Use any of these accounts:

### Admin Account
- **Username**: `admin`
- **Password**: `admin123`
- **Role**: admin

### User Account
- **Username**: `user`
- **Password**: `user123`
- **Role**: user

### Demo Account
- **Username**: `demo`
- **Password**: `demo123`
- **Role**: user

---

## Quick Access

1. Start the application:
   ```bash
   docker-compose up --build
   ```

2. Open browser: http://localhost:5173

3. Login with any credentials above (e.g., `demo` / `demo123`)

4. Navigate to **Marketplace** in the sidebar menu

---

## For Marketplace Demo

The marketplace feature works with any of the above accounts. We recommend using:
- **Username**: `demo`
- **Password**: `demo123`

No special permissions needed!

---

## Security Note

⚠️ **These are development credentials only!**

For production:
- Change the `AUTH_SECRET_KEY` in docker-compose.yml
- Use environment variables for user management
- Consider using a proper database and OAuth provider
