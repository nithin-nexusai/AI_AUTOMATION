# CHICX Bot - Quick Deployment Guide

## 🚀 Quick Start

### Prerequisites
- AWS account
- SSH key pair (`.pem` file)
- Domain: thechicx.com (with subdomain access)
- 2-3 hours

### Cost: ₹2,138/month (₹669 first year with Free Tier!)

### Step 1: Create EC2 Instance
```bash
# AWS Console > EC2 > Launch Instance
Instance Type: t3.small (2 vCPU, 2GB RAM)  ← Cheaper!
AMI: Ubuntu 22.04 LTS
Region: ap-south-1 (Mumbai)
Storage: 30GB gp3
Security Group: Allow ports 22, 80, 443
```

### Step 2: Connect and Setup
```bash
# Connect to EC2
ssh -i chicx-bot-key.pem ubuntu@YOUR_EC2_IP

# Run automated setup
curl -fsSL https://raw.githubusercontent.com/YOUR_REPO/main/scripts/init.sh | bash
```

### Step 3: Deploy Bot
```bash
# Clone repository
cd /opt
sudo git clone YOUR_REPO chicx-bot
sudo chown -R ubuntu:ubuntu chicx-bot
cd chicx-bot

# Configure environment
cp .env.production .env
nano .env  # Update secrets and credentials

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Run migrations
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head

# Test
curl http://localhost:8000/health
```

### Step 4: Setup SSL Certificate (FREE)
```bash
# Install Certbot
sudo apt install -y certbot

# Get certificate for subdomain
sudo certbot certonly --standalone \
  -d bot.thechicx.com \
  --non-interactive \
  --agree-tos \
  --email admin@thechicx.com

# Copy certificates
sudo cp /etc/letsencrypt/live/bot.thechicx.com/fullchain.pem /data/nginx/ssl/
sudo cp /etc/letsencrypt/live/bot.thechicx.com/privkey.pem /data/nginx/ssl/
sudo chown -R ubuntu:ubuntu /data/nginx/ssl

# Restart Nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

### Step 5: Configure DNS
```bash
# In Hostinger DNS Management:
Type: A
Name: bot
Value: YOUR_EC2_ELASTIC_IP
TTL: 300

# Wait 5-10 minutes for propagation
# Test: ping bot.thechicx.com
```

### Step 6: Update Service URLs
```bash
# Update WhatsApp webhook in Meta Business Suite
Old: https://ngrok-url/webhooks/whatsapp
New: https://bot.thechicx.com/webhooks/whatsapp

# Update Bolna tools in Bolna Dashboard
Old: https://ngrok-url/api/*
New: https://thechicx.com/api/*  (calls Hostinger directly)
```

### Step 7: Setup Monitoring
```bash
ssh -i chicx-bot-key.pem ubuntu@YOUR_EC2_IP
cd /opt/chicx-bot
./scripts/setup-monitoring.sh
```

## 📚 Documentation

- **AWS Deployment Guide:** [docs/AWS_DEPLOYMENT_GUIDE.md](../docs/AWS_DEPLOYMENT_GUIDE.md) ← **FOLLOW THIS!**
- **Backend Integration:** [docs/BACKEND_INTEGRATION_GUIDE.md](../docs/BACKEND_INTEGRATION_GUIDE.md)
- **Monitoring Setup:** [scripts/setup-monitoring.sh](scripts/setup-monitoring.sh)

## 🛠️ Deployment Scripts

### Automated Deployment
```bash
# From your local machine
./scripts/deploy.sh production
```

### Manual Deployment
```bash
# On EC2 instance
cd /opt/chicx-bot
git pull
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head
```

### Rollback
```bash
./scripts/deploy.sh --rollback
```

## 📊 Monitoring

### View Dashboard
```bash
ssh -i chicx-bot-key.pem ubuntu@YOUR_EC2_IP
/opt/chicx-bot/scripts/dashboard.sh

# Or live updates
watch -n 5 /opt/chicx-bot/scripts/dashboard.sh
```

### View Logs
```bash
# All logs
docker-compose -f docker-compose.prod.yml logs -f

# App logs only
docker-compose -f docker-compose.prod.yml logs -f app

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100 app

# Filter by keyword
docker-compose -f docker-compose.prod.yml logs -f app | grep whatsapp
```

### Health Checks
```bash
# Manual health check
/opt/chicx-bot/scripts/health-check.sh

# View health check logs
tail -f /var/log/chicx-bot/health-check.log
```

## 🔧 Maintenance

### Restart Services
```bash
# Restart all
docker-compose -f docker-compose.prod.yml restart

# Restart app only
docker-compose -f docker-compose.prod.yml restart app

# Restart with rebuild
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
```

### Update Code
```bash
cd /opt/chicx-bot
git pull
docker-compose -f docker-compose.prod.yml restart app
```

### Backup Database
```bash
/opt/chicx-bot/scripts/backup.sh

# Backups stored in: /opt/chicx-bot-backups/
```

### View Metrics
```bash
# Performance metrics
tail -f /var/log/chicx-bot/metrics.log

# System resources
htop

# Docker stats
docker stats
```

## 🚨 Troubleshooting

### Bot Not Responding
```bash
# Check container status
docker-compose -f docker-compose.prod.yml ps

# Check logs for errors
docker-compose -f docker-compose.prod.yml logs --tail=100 app | grep -i error

# Restart if needed
docker-compose -f docker-compose.prod.yml restart app
```

### High Memory Usage
```bash
# Check memory
free -h

# Check Docker memory
docker stats

# Restart services
docker-compose -f docker-compose.prod.yml restart
```

### Database Issues
```bash
# Check database connection
docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U chicxadmin

# View database logs
docker-compose -f docker-compose.prod.yml logs postgres

# Restart database
docker-compose -f docker-compose.prod.yml restart postgres
```

### WhatsApp Webhook Not Working
```bash
# Test webhook
curl "https://bot.thechicx.com/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=chicx_webhook_verify_2025&hub.challenge=test"

# Check logs
docker-compose -f docker-compose.prod.yml logs -f app | grep whatsapp

# Verify Meta webhook settings
# - URL: https://bot.thechicx.com/webhooks/whatsapp
# - Token: chicx_webhook_verify_2025
```

## 📞 Support

### Useful Commands
```bash
# SSH to server
ssh -i chicx-bot-key.pem ubuntu@YOUR_EC2_IP

# View dashboard
/opt/chicx-bot/scripts/dashboard.sh

# View logs
cd /opt/chicx-bot && docker-compose -f docker-compose.prod.yml logs -f app

# Restart bot
cd /opt/chicx-bot && docker-compose -f docker-compose.prod.yml restart app

# Check status
cd /opt/chicx-bot && docker-compose -f docker-compose.prod.yml ps

# Run health check
/opt/chicx-bot/scripts/health-check.sh
```

### Emergency Rollback
```bash
# Rollback to previous deployment
./scripts/deploy.sh --rollback

# Or manually restore from backup
cd /opt/chicx-bot-backups
# Find latest backup
ls -lt | head -5
# Restore .env and database
```

## 🎯 Production URLs

After deployment, your bot will be available at:

- **Website:** https://thechicx.com/ (Hostinger)
- **Bot Webhooks:** https://bot.thechicx.com/webhooks/ (AWS)
- **Health Check:** https://bot.thechicx.com/admin/health
- **WhatsApp Webhook:** https://bot.thechicx.com/webhooks/whatsapp
- **Bolna Webhooks:** https://bot.thechicx.com/webhooks/bolna/*
- **CHICX Webhooks:** https://bot.thechicx.com/webhooks/chicx/*

## 💰 Cost Estimate

Monthly AWS costs (Subdomain Approach):
- EC2 t3.small: ₹1,245
- EBS 30GB: ₹200
- Elastic IP: FREE
- Data Transfer: ₹75
- Route 53: ₹42
- Backups: ₹150
- CloudWatch: ₹100
- GST (18%): ₹326
- **Total: ₹2,138/month**

**First Year (Free Tier): ₹669/month** 🎉
**Reserved Instance (1Y): ₹1,283/month**

**Savings vs CloudFront: ₹2,462/month (₹29,544/year)** 💰

## ✅ Deployment Checklist

- [ ] EC2 instance created
- [ ] Dependencies installed
- [ ] Bot deployed
- [ ] Database migrated
- [ ] FAQs imported
- [ ] Subdomain DNS configured
- [ ] SSL certificate obtained (Let's Encrypt)
- [ ] Nginx configured with SSL
- [ ] WhatsApp webhook updated
- [ ] Bolna tools updated
- [ ] Monitoring setup
- [ ] Health checks passing
- [ ] All tests passing

## 🎉 Next Steps

After deployment:
1. Monitor logs for 24 hours
2. Test all features
3. Setup automated backups
4. Configure alerts
5. Document any issues
6. Train team on monitoring

When backend APIs are ready:
1. No redeployment needed
2. Just restart bot: `docker-compose -f docker-compose.prod.yml restart app`
3. Test order features
4. Monitor for issues

---

**Need Help?**
- AWS Guide: [docs/AWS_DEPLOYMENT_GUIDE.md](../docs/AWS_DEPLOYMENT_GUIDE.md) ← **PRIMARY GUIDE**
- Backend Integration: [docs/BACKEND_INTEGRATION_GUIDE.md](../docs/BACKEND_INTEGRATION_GUIDE.md)
- Issues: Create GitHub issue
- Email: devops@thechicx.com