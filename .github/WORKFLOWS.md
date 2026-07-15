# GitHub Actions Workflows Documentation

This project uses automated CI/CD pipelines to ensure code quality, security, and reliable deployments.

## 🔄 Workflow Overview

```
┌─────────────────┐
│   Push/PR       │
└────────┬────────┘
         │
    ┌────┴────┬───────────┬──────────────┐
    │          │           │              │
    ▼          ▼           ▼              ▼
 Unit Tests  Docker Test  Auto-Fix   AI Diagnostics
    │          │           │              │
    └────┬─────┴────┬──────┴──────┬───────┘
         │          │             │
         ▼          ▼             ▼
    Reports   Push to Registry  Issues & PRs
```

## 📋 Individual Workflows

### 1. **Unit Tests** (`unit-tests.yml`)
Tests the Python code before Docker build.

**Triggers:**
- On every push to `main`/`master`
- On pull requests

**What it does:**
- Runs pytest on Python 3.10, 3.11, 3.12
- Generates coverage reports
- Uploads to Codecov
- Archives test artifacts

**Status Badge:**
```markdown
![Unit Tests](https://github.com/YOUR-REPO/actions/workflows/unit-tests.yml/badge.svg)
```

### 2. **Docker Test Build** (`docker-test.yml`)
Verifies Docker image can be built and runs container tests.

**Triggers:**
- On every push to `main`/`master`
- On pull requests

**What it does:**
- Builds Docker image from Dockerfile
- Starts container with health checks
- Tests `/health` endpoint
- Tests `/docs` endpoint
- Runs Trivy security scan
- Uploads security results to GitHub Security tab

**Key Checks:**
```bash
✅ Docker image builds successfully
✅ Container starts and is healthy
✅ API endpoints respond correctly
✅ No critical security vulnerabilities
```

### 3. **Docker Build & Push** (`docker-build-push.yml`)
Builds and pushes image to Docker Hub.

**Triggers:**
- On push to `main`/`master` (tag: `latest`)
- On git tags like `v1.0.0` (tag: version)
- NOT on pull requests (only builds, doesn't push)

**What it does:**
- Builds Docker image with Buildx
- Tags appropriately (latest, version, branch)
- Pushes to Docker Hub (if not PR)
- Uses layer caching for faster builds

**Image Naming:**
```
docker.io/{DOCKERHUB_USERNAME}/mediapipe-nsfw-api:latest
docker.io/{DOCKERHUB_USERNAME}/mediapipe-nsfw-api:v1.0.0
docker.io/{DOCKERHUB_USERNAME}/mediapipe-nsfw-api:main-{commit-sha}
```

### 4. **Dependabot Updates** (`dependabot.yml`)
Automatically checks for dependency updates and security patches.

**Schedule:**
- Python packages: Monday 3:00 UTC
- Docker base image: Monday 4:00 UTC
- GitHub Actions: Tuesday 3:00 UTC

**What it does:**
- Creates Pull Requests for updates
- Groups up to 5 PRs for Python, 3 for Docker, 2 for Actions
- Mentions you for review
- Tags with semantic commit messages

**Example PR:**
```
Title: chore(deps): bump pillow from 10.1.0 to 10.2.0
Auto-created security update
```

### 5. **Auto-Fix Build Failures** (`auto-fix-build-failures.yml`)
Automatically attempts to fix common build issues.

**Triggers:**
- When `docker-test.yml` or `docker-build-push.yml` fails
- Manual trigger via workflow_dispatch

**What it does:**
- Analyzes failure logs
- Creates a GitHub Issue with findings
- Attempts automatic fixes:
  - Updates `requirements.txt` pinned versions
  - Checks Dockerfile compatibility
  - Verifies base image versions
- Creates a PR with proposed fixes (if changes made)

**Automatic Fixes Applied:**
```python
- Converts "==" to ">=" for minor version flexibility
- Checks Python version compatibility
- Validates Dockerfile syntax
```

### 6. **AI Agent Diagnostics** (`ai-agent-diagnostics.yml`)
Uses Claude AI to intelligently diagnose and suggest fixes.

**Triggers:**
- When `docker-test.yml` or `docker-build-push.yml` fails
- Manual trigger via workflow_dispatch

**What it does:**
- Fetches failure logs and code context
- Uses Claude AI (Opus 4.1) to analyze
- Creates detailed diagnostic issue
- Provides implementation plan
- Creates PR with AI-recommended fixes

**AI Analysis Includes:**
- Root cause identification
- Severity assessment (critical/high/medium/low)
- 2-3 specific fix recommendations
- Implementation code/commands

**Requirements:**
- `ANTHROPIC_API_KEY` secret must be set

---

## 🔑 Required GitHub Secrets

Add these to `Settings → Secrets and variables → Actions`:

### For Docker Hub Pushes
```
DOCKERHUB_USERNAME    = your-docker-hub-username
DOCKERHUB_TOKEN       = your-docker-hub-personal-access-token
```

[Get Docker Hub Token](https://hub.docker.com/settings/security)

### For AI Diagnostics (Optional)
```
ANTHROPIC_API_KEY     = sk-ant-... (from console.anthropic.com)
```

---

## 🚀 Usage Examples

### Deploy a new version
```bash
# Trigger build, test, and push to Docker Hub
git tag v1.2.3
git push origin v1.2.3
# → Automatically builds, tests, pushes, and deploys to Plesk
```

### Manual diagnostics
```
Go to Actions → "AI Agent Diagnostics" → Run workflow → Branch: main
# → AI analyzes current state and suggests improvements
```

### Check test coverage
```
Go to Actions → "Unit Tests" → Latest run → Artifacts
# → Download test-results-x.x.x and open htmlcov/index.html
```

---

## 📊 Status Checks

All pull requests require these status checks to pass:
- ✅ Unit Tests (Python 3.10, 3.11, 3.12)
- ✅ Docker Test Build
- ✅ Code scanning (Trivy)

---

## 🔍 Viewing Results

### Test Coverage
- GitHub: Actions → Unit Tests → Codecov
- Artifacts: test-results-*.zip (contains htmlcov/)

### Security Scans
- GitHub: Security → Code scanning → Trivy results
- Inline: In PR checks

### Logs
- GitHub: Actions → Specific workflow → Run details

### Build Artifacts
- Docker Hub: https://hub.docker.com/r/YOUR-USERNAME/mediapipe-nsfw-api

---

## 🐛 Troubleshooting

### "Build failed - Dependency error"
The auto-fix workflow will:
1. Create issue with analysis
2. Update `requirements.txt`
3. Create PR with fixes
→ Review and merge the fix PR

### "Container health check failed"
1. Check workflow logs for errors
2. AI diagnostics will analyze
3. Usually caused by:
   - Port conflicts
   - Missing environment variables
   - Startup timeout too short

### "Trivy found critical vulnerabilities"
Dependabot will automatically create a PR with security patches
→ Merge security update PR

### "API endpoint returns 500"
Check:
1. Container logs in workflow
2. Environment variables in docker-compose.yml
3. Run tests locally: `pytest tests/ -v`

---

## 📈 Metrics & Monitoring

Track these metrics:
- **Build Time**: Should be <5 min (cached)
- **Test Coverage**: Aim for >80%
- **Dependency Updates**: Check Dependabot PRs weekly
- **Security Scans**: Should have 0 critical vulnerabilities

---

## 🔗 Related Files

- [requirements.txt](../requirements.txt) - Python dependencies
- [Dockerfile](../Dockerfile) - Docker image definition
- [docker-compose.yml](../docker-compose.yml) - Container orchestration
- [tests/](../tests/) - Unit test files
- [.env.example](../.env.example) - Environment variables

---

Generated with ❤️ by CI/CD Pipeline Setup
