# AWS Deployment Guide - CHICX WhatsApp Bot
## Complete Guide for Mumbai Region (ap-south-1)

**Last Updated:** April 11, 2026  
**Region:** Asia Pacific (Mumbai)  
**Currency:** Indian Rupees (INR)

---

## 📋 Table of Contents

1. [Cost Comparison](#cost-comparison)
2. [Recommended Setup](#recommended-setup)
3. [Option 1: Single EC2 with Docker (Recommended)](#option-1-single-ec2-with-docker-recommended)
4. [Option 2: Managed Services](#option-2-managed-services)
5. [Redis: Keep or Remove?](#redis-keep-or-remove)
6. [ALB: Do You Need It?](#alb-do-you-need-it)
7. [Scaling Strategy](#scaling-strategy)
8. [FAQ](#faq)

---

## 💰 Cost Comparison

### All Deployment Options

| Setup | Monthly Cost | Annual Cost | Best For |
|-------|--------------|-------------|----------|
| **Single EC2 + Docker (Recommended)** | ₹2,138 | ₹25,656 | Startups, <5K msg/day |
| **Single EC2 + Docker (Free Tier)** | ₹1,080 | ₹12,960 | First year only |
| **Single EC2 + Docker (Reserved 1Y)** | ₹1,283 | ₹15,396 | Best value after year 1 |
| **Managed (RDS + ElastiCache, No ALB)** | ₹4,165 | ₹49,980 | Growing business |
| **Managed (Full: RDS + ElastiCache + ALB)** | ₹5,733 | ₹68,796 | Enterprise, >10K msg/day |

### Savings Comparison

| vs Managed Services | Monthly Savings | Annual Savings |
|---------------------|----------------|----------------|
| Single EC2 (On-Demand) | ₹3,595 | ₹43,140 |
| Single EC2 (Free Tier) | ₹4,653 | ₹55,836 |
| Single EC2 (Reserved) | ₹4,450 | ₹53,400 |

---

## 🎯 Recommended Setup

### For CHICX (Current Stage)

**✅ Single EC2 with Docker**

**Why?**
- 63% cheaper than managed services
- Handles 5,000+ messages/day easily
- Simple to manage (one server)
- Full control over all components
- Easy to migrate later

**Monthly Cost:** ₹2,138 (₹1,080 with Free Tier)

---

## Option 1: Single EC2 with Docker (Recommended)

### Architecture

```
┌─────────────────────────────────────────────────┐
│         Single EC2 Instance (t3.small)          │
│                                                 │
│  ┌───────────────────────────────────────────┐ │
│  │         Docker Compose Stack              │ │
│  │                                           │ │
│  │  ┌─────────────────────────────────────┐ │ │
│  │  │  Nginx (SSL + Reverse Proxy)        │ │ │
│  │  │  Ports: 80, 443                     │ │ │
│  │  └─────────────────────────────────────┘ │ │
│  │                 ↓                         │ │
│  │  ┌─────────────────────────────────────┐ │ │
│  │  │  FastAPI App                        │ │ │
│  │  │  Port: 8000                         │ │ │
│  │  └─────────────────────────────────────┘ │ │
│  │         ↓              ↓                  │ │
│  │  ┌──────────────┐  ┌─────────────────┐  │ │
│  │  │ PostgreSQL   │  │ Redis           │  │ │
│  │  │ + pgvector   │  │ Cache           │  │ │
│  │  └──────────────┘  └─────────────────┘  │ │
│  └───────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
         │
         ▼
    Elastic IP (FREE)
         │
         ▼
    Route 53 DNS
```

### Cost Breakdown

| Item | Configuration | Monthly Cost (₹) |
|------|--------------|-----------------|
| **EC2 Instance** | t3.small (2 vCPU, 2GB RAM) | ₹1,245 |
| **EBS Storage** | 30GB gp3 SSD | ₹200 |
| **Elastic IP** | 1 static IP | **FREE** |
| **Data Transfer** | 10GB outbound | ₹75 |
| **Route 53** | DNS hosting | ₹42 |
| **Backups** | EBS snapshots | ₹150 |
| **CloudWatch** | Basic monitoring | ₹100 |
| **Subtotal** | | **₹1,812** |
| **GST (18%)** | | **₹326** |
| **TOTAL** | | **₹2,138/month** |

**With Free Tier (Year 1):** ₹1,080/month  
**With Reserved Instance (1Y):** ₹1,283/month

### Resource Usage

| Container | CPU | Memory | Disk |
|-----------|-----|--------|------|
| FastAPI App | 10-20% | 200-300MB | 100MB |
| PostgreSQL | 5-10% | 200-400MB | 2-5GB |
| Redis | 2-5% | 50-100MB | 50-200MB |
| Nginx | 1-2% | 10-20MB | 10MB |
| **Total** | **20-40%** | **500-900MB** | **3-6GB** |

**Capacity:** Can handle 5,000-10,000 messages/day

### Complete Setup Guide

#### Step 1: Launch EC2 Instance

```bash
# Create key pair
aws ec2 create-key-pair \
  --key-name chicx-key \
  --query 'KeyMaterial' \
  --output text > chicx-key.pem

chmod 400 chicx-key.pem

# Launch t3.small instance
aws ec2 run-instances \
  --image-id ami-0f58b397bc5c1f2e8 \
  --instance-type t3.small \
  --key-name chicx-key \
  --security-group-ids sg-xxxxx \
  --subnet-id subnet-public-xxxxx \
  --block-device-mappings '[{
    "DeviceName":"/dev/xvda",
    "Ebs":{
      "VolumeSize":30,
      "VolumeType":"gp3",
      "DeleteOnTermination":false
    }
  }]' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=chicx-bot}]'
```

#### Step 2: Configure Security Group

```bash
# Create security group
aws ec2 create-security-group \
  --group-name chicx-sg \
  --description "CHICX Bot Security Group" \
  --vpc-id vpc-xxxxx

# Allow HTTP, HTTPS, SSH
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxx \
  --ip-permissions \
    IpProtocol=tcp,FromPort=80,ToPort=80,IpRanges='[{CidrIp=0.0.0.0/0}]' \
    IpProtocol=tcp,FromPort=443,ToPort=443,IpRanges='[{CidrIp=0.0.0.0/0}]' \
    IpProtocol=tcp,FromPort=22,ToPort=22,IpRanges='[{CidrIp=YOUR_IP/32}]'
```

#### Step 3: Allocate Elastic IP

```bash
# Allocate Elastic IP
aws ec2 allocate-address --domain vpc

# Associate with instance
aws ec2 associate-address \
  --instance-id i-xxxxx \
  --allocation-id eipalloc-xxxxx
```

#### Step 4: Install Docker

```bash
# SSH into instance
ssh -i chicx-key.pem ec2-user@YOUR_ELASTIC_IP

# Update system
sudo yum update -y

# Install Docker
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker ec2-user

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Git
sudo yum install -y git

# Create directories
sudo mkdir -p /data/postgres /data/redis /data/nginx/ssl /opt/chicx-bot
sudo chown -R ec2-user:ec2-user /data /opt/chicx-bot
```

#### Step 5: Docker Compose Configuration

Create `/opt/chicx-bot/docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: pgvector/pgvector:pg15
    container_name: chicx-postgres
    environment:
      POSTGRES_DB: chicx
      POSTGRES_USER: chicxadmin
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - /data/postgres:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U chicxadmin -d chicx"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - chicx-network

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: chicx-redis
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - /data/redis:/data
    ports:
      - "6379:6379"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - chicx-network

  # FastAPI Application
  app:
    build: .
    container_name: chicx-app
    environment:
      - DATABASE_URL=postgresql+asyncpg://chicxadmin:${POSTGRES_PASSWORD}@postgres:5432/chicx
      - REDIS_URL=redis://redis:6379/0
      - WHATSAPP_PHONE_NUMBER_ID=${WHATSAPP_PHONE_NUMBER_ID}
      - WHATSAPP_ACCESS_TOKEN=${WHATSAPP_ACCESS_TOKEN}
      - WHATSAPP_VERIFY_TOKEN=${WHATSAPP_VERIFY_TOKEN}
      - WHATSAPP_APP_SECRET=${WHATSAPP_APP_SECRET}
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
    volumes:
      - ./logs:/app/logs
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/admin/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - chicx-network

  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    container_name: chicx-nginx
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - /data/nginx/ssl:/etc/nginx/ssl:ro
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - app
    restart: unless-stopped
    networks:
      - chicx-network

networks:
  chicx-network:
    driver: bridge
```

#### Step 6: Nginx Configuration

Create `/opt/chicx-bot/nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    
    # Upstream
    upstream app {
        server app:8000;
    }

    # HTTP Server (redirect to HTTPS)
    server {
        listen 80;
        server_name bot.thechicx.com;

        # Let's Encrypt challenge
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        # Redirect to HTTPS
        location / {
            return 301 https://$server_name$request_uri;
        }
    }

    # HTTPS Server
    server {
        listen 443 ssl http2;
        server_name bot.thechicx.com;

        # SSL Configuration
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        # Security Headers
        add_header Strict-Transport-Security "max-age=31536000" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;

        # Proxy to FastAPI
        location / {
            limit_req zone=api_limit burst=20 nodelay;
            
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        # Health check (no rate limit)
        location /admin/health {
            proxy_pass http://app;
        }
    }
}
```

#### Step 7: SSL Certificate

```bash
# Install Certbot
sudo yum install -y certbot

# Get certificate
sudo certbot certonly --standalone \
  -d bot.thechicx.com \
  --non-interactive \
  --agree-tos \
  --email admin@thechicx.com

# Copy certificates
sudo cp /etc/letsencrypt/live/bot.thechicx.com/fullchain.pem /data/nginx/ssl/
sudo cp /etc/letsencrypt/live/bot.thechicx.com/privkey.pem /data/nginx/ssl/
sudo chown -R ec2-user:ec2-user /data/nginx/ssl

# Auto-renewal cron job
echo "0 0 * * * certbot renew --quiet && cp /etc/letsencrypt/live/bot.thechicx.com/*.pem /data/nginx/ssl/ && docker-compose -f /opt/chicx-bot/docker-compose.prod.yml restart nginx" | sudo crontab -
```

#### Step 8: Deploy Application

```bash
# Clone repository
cd /opt/chicx-bot
git clone https://github.com/your-org/chicx-bot.git .

# Create .env file
cat > .env << 'EOF'
POSTGRES_PASSWORD=your_secure_password
WHATSAPP_PHONE_NUMBER_ID=your_phone_id
WHATSAPP_ACCESS_TOKEN=your_token
WHATSAPP_VERIFY_TOKEN=your_verify_token
WHATSAPP_APP_SECRET=your_secret
OPENROUTER_API_KEY=your_key
EOF

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# Run migrations
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head

# Generate embeddings
docker-compose -f docker-compose.prod.yml exec app python scripts/generate_embeddings.py
```

#### Step 9: Automated Backups

Create `/opt/chicx-bot/scripts/backup.sh`:

```bash
#!/bin/bash

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/data/backups"

mkdir -p $BACKUP_DIR

# Backup PostgreSQL
docker-compose -f /opt/chicx-bot/docker-compose.prod.yml exec -T postgres \
  pg_dump -U chicxadmin chicx | gzip > $BACKUP_DIR/postgres_$DATE.sql.gz

# Backup Redis
docker-compose -f /opt/chicx-bot/docker-compose.prod.yml exec -T redis \
  redis-cli SAVE
cp /data/redis/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# Clean old backups (keep last 7 days)
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete
find $BACKUP_DIR -name "*.rdb" -mtime +7 -delete

echo "Backup completed: $DATE"
```

```bash
chmod +x /opt/chicx-bot/scripts/backup.sh

# Add to crontab (daily at 2 AM)
echo "0 2 * * * /opt/chicx-bot/scripts/backup.sh >> /var/log/backup.log 2>&1" | crontab -
```

### Pros & Cons

**✅ Advantages:**
- 63% cheaper (₹2,138 vs ₹5,733)
- Simple management (one server)
- Full control
- Easy to migrate
- Docker portability

**❌ Disadvantages:**
- Single point of failure
- Manual scaling
- You manage backups
- No auto-scaling

---

## Option 2: Managed Services

### Architecture

```
Internet → Route 53 → ALB (SSL) → EC2 → RDS PostgreSQL
                                      → ElastiCache Redis
```

### Cost Breakdown

| Service | Configuration | Monthly Cost (₹) |
|---------|--------------|-----------------|
| **EC2** | t3.micro (2 vCPU, 1GB RAM) | ₹623 |
| **RDS PostgreSQL** | db.t3.micro (1 vCPU, 1GB RAM) | ₹1,245 |
| **ElastiCache Redis** | cache.t3.micro (0.5GB) | ₹996 |
| **ALB** | Application Load Balancer | ₹1,328 |
| **EBS** | 20GB gp3 SSD | ₹133 |
| **Other** | S3, CloudWatch, DNS, Backups | ₹550 |
| **Subtotal** | | **₹4,858** |
| **GST (18%)** | | **₹875** |
| **TOTAL** | | **₹5,733/month** |

### When to Use

**Migrate to managed services when:**
- Traffic exceeds 10,000 messages/day
- Need 99.9%+ uptime
- Team grows (need managed services)
- Revenue justifies higher costs
- Multi-region deployment needed

**Timeline:** 12-24 months for most startups

---

## Redis: Keep or Remove?

### What Redis Does

Redis is used for **3 critical functions**:

1. **Message Deduplication** - Prevents processing same message twice
2. **Conversation Context** - Stores last 10 messages for context
3. **Order Tracking** - Maps voice call IDs to orders

### Impact Without Redis

| Feature | Status | Impact |
|---------|--------|--------|
| Message Deduplication | ❌ Broken | Duplicate responses sent |
| Conversation Memory | ❌ Broken | Bot forgets context |
| Voice Confirmations | ❌ Broken | Feature doesn't work |
| **Overall Quality** | 📉 Poor | **UNACCEPTABLE** |

### Cost Comparison

| Setup | Monthly Cost | Quality |
|-------|--------------|---------|
| **With Redis (on EC2)** | ₹2,138 | ✅ Perfect |
| **With ElastiCache** | ₹3,134 | ✅ Perfect |
| **Without Redis** | ₹1,142 | ❌ Broken |

### Recommendation

**✅ Keep Redis, run it on EC2 (FREE)**

Redis on EC2 costs ₹0 extra and provides full functionality. Don't remove it.

---

## ALB: Do You Need It?

### What ALB Does

| Feature | Do You Need It? | Alternative |
|---------|----------------|-------------|
| Load Balancing | ❌ No (1 server) | Direct connection |
| SSL Termination | ✅ Yes | Nginx + Let's Encrypt (FREE) |
| Health Checks | ✅ Yes | Custom script (FREE) |
| Auto-Scaling | ❌ No | Manual scaling |
| Multi-AZ | ❌ No | Not critical |

### Cost Impact

| Setup | Monthly Cost | Savings |
|-------|--------------|---------|
| **With ALB** | ₹5,733 | - |
| **Without ALB (Elastic IP)** | ₹4,165 | ₹1,568 |
| **Single EC2 (Docker)** | ₹2,138 | ₹3,595 |

### Recommendation

**❌ Don't use ALB for startup phase**

ALB costs ₹1,568/month to route traffic to ONE server. Use Elastic IP + Nginx instead.

**Migrate to ALB when:**
- Running 2+ EC2 instances
- Need zero-downtime deployments
- Traffic exceeds 5,000 messages/day

---

## 📈 Scaling Strategy

### Phase 1: Startup (0-12 months)

**Setup:** Single EC2 with Docker  
**Cost:** ₹1,080/month (Free Tier) → ₹2,138/month  
**Capacity:** 5,000 messages/day  
**When to scale:** Traffic consistently >3,000 messages/day

### Phase 2: Growth (12-24 months)

**Setup:** Larger EC2 (t3.medium) with Docker  
**Cost:** ₹2,490/month  
**Capacity:** 15,000 messages/day  
**When to scale:** Traffic consistently >10,000 messages/day

### Phase 3: Scale (24+ months)

**Setup:** Managed Services (RDS + ElastiCache + ALB + Auto Scaling)  
**Cost:** ₹5,733/month  
**Capacity:** 50,000+ messages/day  
**When to scale:** Need 99.9%+ uptime, multi-region

---

## ❓ FAQ

### Q: Which setup should I choose?

**A:** Single EC2 with Docker (Option 1)

**Reasons:**
- 63% cheaper
- Handles your current traffic easily
- Simple to manage
- Easy to migrate later

### Q: Can I remove Redis to save money?

**A:** No, Redis is critical

**Impact:** Bot will be broken without Redis (duplicate messages, no memory, broken features)

**Solution:** Run Redis on EC2 (costs ₹0 extra)

### Q: Do I need Application Load Balancer?

**A:** No, not for startup phase

**Reason:** ALB costs ₹1,568/month to route traffic to ONE server

**Alternative:** Use Elastic IP + Nginx (FREE)

### Q: When should I migrate to managed services?

**A:** When traffic exceeds 10,000 messages/day or need 99.9%+ uptime

**Timeline:** 12-24 months for most startups

### Q: What about backups?

**A:** Automated daily backups included in all setups

**Single EC2:** Bash script + cron job  
**Managed:** AWS automated backups

### Q: Can I scale later?

**A:** Yes, easily

**Migration path:**
1. Start: Single EC2 with Docker (₹2,138/month)
2. Grow: Larger EC2 instance (₹2,490/month)
3. Scale: Managed services (₹5,733/month)

**Downtime:** ~5-10 minutes per migration

---

## 📊 Final Recommendation

### For CHICX (Current Stage)

**✅ Single EC2 with Docker**

**Monthly Cost:**
- Year 1: ₹1,080 (with Free Tier)
- Year 2+: ₹2,138 (on-demand) or ₹1,283 (reserved)

**Capacity:** 5,000-10,000 messages/day

**Why?**
- 63% cheaper than managed services
- Handles your traffic easily
- Simple to manage
- Full control
- Easy to migrate later

**Next Steps:**
1. Launch t3.small EC2 instance
2. Install Docker + Docker Compose
3. Deploy using docker-compose.prod.yml
4. Setup SSL with Let's Encrypt (FREE)
5. Configure automated backups
6. Monitor and scale when needed

---

## 📞 Support

- **AWS India:** +91-80-6750-2000
- **Email:** aws-india-sales@amazon.com
- **Documentation:** https://docs.aws.amazon.com
- **Pricing Calculator:** https://calculator.aws

---

**Last Updated:** April 11, 2026  
**Version:** 2.0 (Consolidated)  
**Maintained By:** CHICX Tech Team