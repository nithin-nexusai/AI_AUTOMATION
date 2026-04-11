# GitHub Actions CI/CD Setup Guide

## Overview

This guide explains how to set up automated testing and deployment using GitHub Actions (FREE for public repos, 2,000 minutes/month for private repos).

---

## 🎯 What's Included

### 1. Automated Testing (`.github/workflows/test.yml`)
- Runs on every pull request and push to `develop`
- Tests with PostgreSQL + Redis
- Code linting (flake8, black, isort)
- Test coverage reporting
- Runs in ~3-5 minutes

### 2. Automated Deployment (`.github/workflows/deploy.yml`)
- Runs on push to `main` branch
- Runs tests first
- Deploys to AWS EC2
- Health check verification
- Automatic rollback on failure
- Slack notifications
- Runs in ~5-8 minutes

---

## 📋 Prerequisites

1. GitHub repository (public or private)
2. AWS EC2 instance running
3. SSH access to EC2
4. AWS credentials (for optional features)

---

## 🔧 Setup Instructions

### Step 1: Add GitHub Secrets

Go to your repository → Settings → Secrets and variables → Actions → New repository secret

Add these secrets:

| Secret Name | Description | Example |
|------------|-------------|---------|
| `EC2_HOST` | Your EC2 public IP or domain | `bot.thechicx.com` or `13.232.xxx.xxx` |
| `EC2_SSH_KEY` | Private SSH key for EC2 | Contents of `chicx-key.pem` |
| `AWS_ACCESS_KEY_ID` | AWS access key (optional) | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key (optional) | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| `SLACK_WEBHOOK_URL` | Slack webhook for notifications (optional) | `https://hooks.slack.com/services/...` |

#### How to Get EC2 SSH Key

```bash
# On your local machine
cat chicx-key.pem

# Copy the entire output including:
# -----BEGIN RSA PRIVATE KEY-----
# ... key content ...
# -----END RSA PRIVATE KEY-----
```

Paste this into the `EC2_SSH_KEY` secret.

### Step 2: Prepare EC2 Instance

SSH into your EC2 instance and run:

```bash
# Create deployment directory
sudo mkdir -p /opt/chicx-bot
sudo chown -R ec2-user:ec2-user /opt/chicx-bot

# Create .env file
cat > /opt/chicx-bot/.env << 'EOF'
POSTGRES_PASSWORD=your_secure_password
WHATSAPP_PHONE_NUMBER_ID=your_phone_id
WHATSAPP_ACCESS_TOKEN=your_token
WHATSAPP_VERIFY_TOKEN=your_verify_token
WHATSAPP_APP_SECRET=your_secret
OPENROUTER_API_KEY=your_key
EOF

# Make deploy script executable
chmod +x /opt/chicx-bot/scripts/deploy.sh
```

### Step 3: Test the Workflow

#### Test Automated Testing

```bash
# Create a new branch
git checkout -b test-ci

# Make a small change
echo "# Test" >> README.md

# Commit and push
git add .
git commit -m "test: trigger CI"
git push origin test-ci

# Create pull request on GitHub
# Tests will run automatically
```

#### Test Automated Deployment

```bash
# Merge to main branch
git checkout main
git merge test-ci
git push origin main

# Deployment will start automatically
# Check progress: GitHub → Actions tab
```

---

## 📊 Workflow Details

### Test Workflow (test.yml)

**Triggers:**
- Pull requests to `main` or `develop`
- Pushes to `develop` branch

**Steps:**
1. Checkout code
2. Set up Python 3.11
3. Start PostgreSQL + Redis services
4. Install dependencies
5. Run linting (flake8, black, isort)
6. Run tests with coverage
7. Upload coverage report
8. Generate test report

**Duration:** ~3-5 minutes  
**Cost:** FREE (uses ~5 minutes per run)

### Deploy Workflow (deploy.yml)

**Triggers:**
- Push to `main` branch
- Manual trigger (workflow_dispatch)

**Steps:**
1. Run all tests
2. Create deployment package
3. Upload to EC2
4. Run deployment script
5. Health check
6. Notify on failure

**Duration:** ~5-8 minutes  
**Cost:** FREE (uses ~8 minutes per run)

---

## 🎨 Customization

### Change Deployment Branch

Edit `.github/workflows/deploy.yml`:

```yaml
on:
  push:
    branches:
      - production  # Change from 'main' to 'production'
```

### Add Staging Environment

Create `.github/workflows/deploy-staging.yml`:

```yaml
name: Deploy to Staging

on:
  push:
    branches:
      - develop

env:
  EC2_HOST: ${{ secrets.STAGING_EC2_HOST }}
  # ... rest of config
```

### Skip CI for Certain Commits

Add `[skip ci]` to commit message:

```bash
git commit -m "docs: update README [skip ci]"
```

### Add More Tests

Edit `.github/workflows/test.yml`:

```yaml
- name: Run security scan
  run: |
    pip install bandit
    bandit -r app/

- name: Check dependencies
  run: |
    pip install safety
    safety check
```

---

## 📈 Monitoring

### View Workflow Runs

1. Go to your repository on GitHub
2. Click "Actions" tab
3. See all workflow runs

### Check Deployment Status

```bash
# SSH into EC2
ssh -i chicx-key.pem ec2-user@YOUR_EC2_IP

# Check running containers
docker-compose -f /opt/chicx-bot/docker-compose.prod.yml ps

# View logs
docker-compose -f /opt/chicx-bot/docker-compose.prod.yml logs -f app
```

### Set Up Slack Notifications

1. Create Slack webhook:
   - Go to https://api.slack.com/apps
   - Create new app
   - Add "Incoming Webhooks"
   - Copy webhook URL

2. Add to GitHub secrets:
   - Name: `SLACK_WEBHOOK_URL`
   - Value: Your webhook URL

3. Notifications will be sent on deployment failure

---

## 🐛 Troubleshooting

### Issue: SSH Connection Failed

**Error:** `Permission denied (publickey)`

**Solution:**
```bash
# Verify SSH key format
cat chicx-key.pem

# Should start with:
# -----BEGIN RSA PRIVATE KEY-----

# Re-add to GitHub secrets with correct format
```

### Issue: Health Check Failed

**Error:** `Health check failed!`

**Solution:**
```bash
# SSH into EC2
ssh -i chicx-key.pem ec2-user@YOUR_EC2_IP

# Check application logs
docker-compose -f /opt/chicx-bot/docker-compose.prod.yml logs app

# Check if services are running
docker-compose -f /opt/chicx-bot/docker-compose.prod.yml ps

# Manually test health endpoint
curl http://localhost:8000/admin/health
```

### Issue: Tests Failing

**Error:** Tests pass locally but fail in CI

**Solution:**
```bash
# Check test environment variables in .github/workflows/test.yml
# Ensure all required env vars are set

# Run tests locally with same environment
cd chicx-bot
export DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/chicx_test
export REDIS_URL=redis://localhost:6379/0
pytest tests/ -v
```

### Issue: Deployment Takes Too Long

**Error:** Workflow times out after 6 hours

**Solution:**
```bash
# Reduce Docker image size
# Add to Dockerfile:
RUN pip install --no-cache-dir -r requirements.txt

# Clean up old images on EC2
ssh -i chicx-key.pem ec2-user@YOUR_EC2_IP
docker system prune -af
```

---

## 💰 Cost Analysis

### GitHub Actions Minutes

| Repository Type | Free Minutes/Month | Cost After |
|----------------|-------------------|------------|
| Public | Unlimited | FREE |
| Private | 2,000 minutes | $0.008/minute |

### Typical Usage

| Workflow | Duration | Runs/Month | Total Minutes |
|----------|----------|------------|---------------|
| Test (PR) | 5 min | 40 | 200 min |
| Deploy | 8 min | 20 | 160 min |
| **Total** | | | **360 min/month** |

**Cost for Private Repo:** FREE (under 2,000 min limit)

---

## 🚀 Best Practices

### 1. Use Branch Protection

Settings → Branches → Add rule:
- Require pull request reviews
- Require status checks (tests must pass)
- Require branches to be up to date

### 2. Cache Dependencies

Already included in workflows:

```yaml
- uses: actions/setup-python@v4
  with:
    python-version: '3.11'
    cache: 'pip'  # Caches pip dependencies
```

### 3. Parallel Jobs

For faster CI, run tests in parallel:

```yaml
strategy:
  matrix:
    test-group: [unit, integration, e2e]

steps:
  - name: Run ${{ matrix.test-group }} tests
    run: pytest tests/${{ matrix.test-group }}/ -v
```

### 4. Deployment Approvals

For production, require manual approval:

```yaml
jobs:
  deploy:
    environment:
      name: production
      url: https://bot.thechicx.com
    # Requires manual approval in GitHub
```

### 5. Rollback Strategy

Already included in `deploy.sh`:
- Automatic backup before deployment
- Health check after deployment
- Automatic rollback on failure

---

## 📚 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Actions Pricing](https://docs.github.com/en/billing/managing-billing-for-github-actions/about-billing-for-github-actions)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [AWS EC2 Documentation](https://docs.aws.amazon.com/ec2/)

---

## ✅ Checklist

Before going live, ensure:

- [ ] All GitHub secrets are added
- [ ] EC2 instance is configured
- [ ] `.env` file exists on EC2
- [ ] Test workflow passes
- [ ] Deploy workflow passes
- [ ] Health check endpoint works
- [ ] Slack notifications configured (optional)
- [ ] Branch protection rules set
- [ ] Team has access to repository

---

## 🎉 You're All Set!

Your CI/CD pipeline is now configured. Every push to `main` will:

1. ✅ Run all tests
2. 🚀 Deploy to EC2
3. 🏥 Verify health
4. 📢 Notify on failure

**Next Steps:**
1. Make a change
2. Push to `main`
3. Watch it deploy automatically!

---

**Last Updated:** April 11, 2026  
**Version:** 1.0  
**Maintained By:** CHICX Tech Team