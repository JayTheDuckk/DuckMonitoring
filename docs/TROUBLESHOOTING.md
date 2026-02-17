# Troubleshooting Guide

## "Not Found" Error

If you're seeing a "Not Found" error, here's how to diagnose and fix it:

### 1. Check Which Service You're Accessing

**Backend API (http://localhost:8000):**
- Should show JSON with API information at the root `/`
- Try: `http://localhost:8000/api/health` - should return `{"status": "healthy"}`
- Try: `http://localhost:8000/api/hosts` - should return `[]` (empty array if no hosts)

**Frontend (http://localhost:3000):**
- Should show the Duck Monitoring dashboard
- If you see "Not Found" here, the frontend might not be running

### 2. Verify Services Are Running

**Check Backend:**
```bash
# In backend directory
cd backend_django
python manage.py runserver
# Should see: "Running on http://0.0.0.0:8000"
```

**Check Frontend:**
```bash
# In frontend directory
cd frontend
npm start
# Should open http://localhost:3000 automatically
```

### 3. Common Issues

**Issue: Backend not running**
- Determine if backend is running
- Verify: Visit `http://localhost:8000/api/health` in browser

**Issue: Frontend can't connect to backend**
- Check: Is backend running on port 8000?
- Check: Browser console for CORS errors
- Verify: `frontend/src/services/api.js` has correct port (8000)

**Issue: Wrong URL**
- Backend API: `http://localhost:8000/api/*`
- Frontend UI: `http://localhost:3000`
- Don't mix them up!

**Issue: Port already in use**
- Backend: Change port with `python manage.py runserver 8001` or edit `config/settings.py`
- Frontend: React dev server will automatically use next available port

### 4. Test API Endpoints

Use curl or your browser to test:

```bash
# Health check
curl http://localhost:8000/api/health

# Get all hosts
curl http://localhost:8000/api/hosts

# Root endpoint (API info)
curl http://localhost:8000/
```

### 5. Check Browser Console

Open browser developer tools (F12) and check:
- Console tab for JavaScript errors
- Network tab to see if API calls are failing
- Look for 404 errors on specific endpoints

### 6. Verify Database

If backend starts but endpoints return errors:
```bash
# Check if database file exists
ls -la backend_django/db.sqlite3

# If it doesn't exist, the app will create it on first run
```

## Still Having Issues?

1. Check that both backend and frontend are running
2. Verify ports match (backend: 8000, frontend: 3000)
3. Check browser console for specific error messages
4. Try accessing the backend API directly in browser: `http://localhost:8000/api/health`

