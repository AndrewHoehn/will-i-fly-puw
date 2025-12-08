# Deployment Guide

## 🚀 Quick Deployment Options

### Option 1: Railway.app (Recommended - $5/month)

**Best for: Reliable hosting with persistent storage**

1. **Prepare your repository**
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-github-repo>
git push -u origin main
```

2. **Deploy to Railway**
   - Go to [railway.app](https://railway.app)
   - Click "Start a New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository
   - Railway will auto-detect the Dockerfile

3. **Configure Environment Variables**
   ```
   RAPIDAPI_KEY=your_key_here
   AVIATIONSTACK_KEY=your_key_here
   BACKUP_ENABLED=true
   BACKUP_INTERVAL_HOURS=24
   ```

4. **Add Persistent Volume**
   - In Railway dashboard, go to your service
   - Click "Volumes" → "New Volume"
   - Mount path: `/app/data`
   - Size: 1GB (plenty for the database)

5. **Add Backup Volume (Optional)**
   - Create second volume for `/app/backups`
   - Or use S3 for cloud backups

6. **Deploy**
   - Railway auto-deploys on every git push
   - Your app will be available at `<your-app>.up.railway.app`

**Cost: ~$5/month for 500 hours + storage**

---

### Option 2: Render.com (Free tier available)

**Best for: Free hosting with automatic backups**

1. **Create Render Blueprint**

Create `render.yaml`:
```yaml
services:
  - type: web
    name: kpuw-tracker
    runtime: docker
    plan: free  # or 'starter' for $7/month
    healthCheckPath: /api/dashboard
    envVars:
      - key: RAPIDAPI_KEY
        sync: false
      - key: AVIATIONSTACK_KEY
        sync: false
      - key: BACKUP_ENABLED
        value: true
    disk:
      name: data
      mountPath: /app/data
      sizeGB: 1
```

2. **Deploy**
   - Connect your GitHub repo at [render.com](https://render.com)
   - Render will auto-deploy using the blueprint
   - Add environment variables in dashboard

3. **Setup Backups**
   - Free tier: Download backups manually via API
   - Paid tier: Use Render's managed backups

**Cost: Free (with limitations) or $7/month**

---

### Option 3: Fly.io (Free tier with persistent volumes)

**Best for: Edge deployment with global reach**

1. **Install Fly CLI**
```bash
brew install flyctl  # macOS
# or
curl -L https://fly.io/install.sh | sh
```

2. **Login and Initialize**
```bash
flyctl auth login
flyctl launch --no-deploy
```

3. **Create `fly.toml`** (auto-generated, verify these settings):
```toml
app = "kpuw-tracker"

[build]
  dockerfile = "Dockerfile"

[env]
  PORT = "8000"
  BACKUP_ENABLED = "true"

[mounts]
  source = "data"
  destination = "/app/data"

[[services]]
  internal_port = 8000
  protocol = "tcp"

  [[services.ports]]
    port = 80
    handlers = ["http"]

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]
```

4. **Create Volume**
```bash
flyctl volumes create data --size 1
```

5. **Set Secrets**
```bash
flyctl secrets set RAPIDAPI_KEY=your_key
flyctl secrets set AVIATIONSTACK_KEY=your_key
```

6. **Deploy**
```bash
flyctl deploy
```

**Cost: Free for 3GB storage + 160GB transfer/month**

---

## 💾 Backup Strategy

### Automated Local Backups

The app automatically creates backups every 24 hours to `/app/backups/`.

**Manual backup:**
```bash
python backend/backup_manager.py
```

**Download backups from server:**
```bash
# Railway
railway run python backend/backup_manager.py
railway volumes download data backups/

# Render
render ssh <service-id>
python backend/backup_manager.py
exit
# Use SFTP to download

# Fly.io
flyctl ssh console
python backend/backup_manager.py
exit
flyctl sftp get /app/backups/ ./local-backups/
```

### Cloud Backups (S3)

1. **Create S3 Bucket**
   - Go to AWS Console → S3
   - Create bucket: `kpuw-flight-backups`
   - Enable versioning

2. **Create IAM User**
   - Create user with S3 write permissions
   - Save access key and secret

3. **Configure Environment Variables**
```bash
S3_BACKUP_BUCKET=kpuw-flight-backups
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
```

4. **Install boto3** (add to requirements.txt):
```
boto3==1.34.0
```

Backups will automatically upload to S3 every 24 hours.

**Cost: ~$0.023/GB/month for S3 Standard**

### Backup Schedule Recommendation

1. **Automated daily backups** to S3 (or platform storage)
2. **Weekly manual exports** to your local machine
3. **Monthly archive** to long-term storage (S3 Glacier)

### Restore from Backup

```bash
# Stop the application
# Replace history.db with backup
cp backups/history_backup_20251203_140000.db backend/history.db
# Restart application
```

---

## 📊 Monitoring & Alerts

### Setup Health Checks

All platforms support health checks via `/api/dashboard` endpoint.

### Simple Uptime Monitoring (Free)

1. **UptimeRobot** (uptimerobot.com)
   - Monitor: `https://your-app.com/api/dashboard`
   - Alert: Email/SMS on downtime
   - Cost: Free for 50 monitors

2. **BetterStack** (betterstack.com)
   - More detailed monitoring
   - Cost: Free tier available

### Database Size Monitoring

Add to your scheduled tasks:
```python
# Check database size weekly
def check_db_size():
    size_mb = os.path.getsize('history.db') / (1024 * 1024)
    if size_mb > 100:  # Alert if > 100MB
        logger.warning(f"Database size: {size_mb:.2f} MB")
```

---

## 🔒 Security Checklist

- [x] API keys stored as environment variables (not in code)
- [x] `.gitignore` excludes sensitive files
- [x] HTTPS enabled (automatic on all platforms)
- [x] CORS configured properly
- [ ] Rate limiting (add if needed for public use)
- [ ] Authentication (add if needed for admin features)

### Optional: Add Rate Limiting

```python
# In api.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.get("/api/dashboard")
@limiter.limit("30/minute")
async def get_dashboard():
    # ... existing code
```

---

## 📈 Cost Breakdown

### Railway.app
- **Compute**: $5/month (Hobby plan)
- **Storage**: Included in Hobby plan
- **Backup (S3)**: ~$0.50/month
- **Total**: ~$5.50/month

### Render.com
- **Compute**: Free or $7/month (Starter)
- **Disk**: $1/GB/month
- **Backup (S3)**: ~$0.50/month
- **Total**: Free or ~$8.50/month

### Fly.io
- **Compute**: Free (within limits)
- **Storage**: Free up to 3GB
- **Backup (S3)**: ~$0.50/month
- **Total**: ~$0.50/month (S3 only)

---

## 🚦 Pre-Launch Checklist

1. **Test locally**
   ```bash
   docker-compose up
   # Verify at http://localhost:8000
   ```

2. **Create GitHub repository**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <repo-url>
   git push -u origin main
   ```

3. **Configure environment variables**
   - Create `.env` from `.env.example`
   - Add API keys

4. **Test backup system**
   ```bash
   python backend/backup_manager.py
   # Verify backup created in backups/
   ```

5. **Choose hosting platform**
   - Create account
   - Connect repository
   - Configure environment variables
   - Add persistent volumes

6. **Deploy**
   - Push to GitHub (auto-deploys)
   - Or use platform CLI

7. **Verify deployment**
   - Check `/api/dashboard` endpoint
   - Test flight predictions
   - Verify scheduler is running

8. **Setup monitoring**
   - Add to UptimeRobot
   - Configure email alerts

9. **Schedule backup downloads**
   - Weekly: Download to local machine
   - Monthly: Archive to long-term storage

---

## 🔧 Maintenance

### Weekly Tasks
- Check backup logs
- Download database backup
- Review application logs

### Monthly Tasks
- Update dependencies
- Review API usage/costs
- Archive old backups

### Quarterly Tasks
- Security audit
- Performance optimization
- Database cleanup (if needed)

---

## 📞 Troubleshooting

### Database locked error
```bash
# Check for multiple processes accessing DB
# Ensure only one app instance is running
```

### Backups not creating
```bash
# Check logs
# Verify backup directory permissions
# Ensure BACKUP_ENABLED=true
```

### Out of storage
```bash
# Increase volume size in platform dashboard
# Or cleanup old backups:
python -c "from backup_manager import BackupManager; BackupManager().cleanup_old_backups(7)"
```

---

**Need help?** Check the main README.md or open an issue on GitHub.
