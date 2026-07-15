# CI/CD Setup - Schnellstart

Du hast jetzt eine **vollständige automatisierte CI/CD-Pipeline** mit:
- ✅ **Unit Tests** (Python 3.10/3.11/3.12)
- ✅ **Docker Build Tests** (mit Health Checks)
- ✅ **Sicherheits-Scans** (Trivy)
- ✅ **Automatische Fixes** (bei Build-Failures)
- ✅ **AI-Agent Diagnostik** (Claude AI)
- ✅ **Docker Hub Push** (automatisch)
- ✅ **Dependabot** (Sicherheits-Updates)

## 🚀 Setup in 3 Minuten

### 1. GitHub Secrets hinzufügen

Gehe zu deinem Repo → **Settings → Secrets and variables → Actions**

Klicke **"New repository secret"** und füge folgende hinzu:

**Docker Hub Credentials:**
```
Name: DOCKERHUB_USERNAME
Value: dein-docker-username
```

```
Name: DOCKERHUB_TOKEN
Value: [Generiere hier: https://hub.docker.com/settings/security]
```

⚠️ **WICHTIG**: Token = Personal Access Token von Docker Hub, NICHT dein Passwort!

### 2. (Optional) Anthropic API Key für AI-Agent

Falls du den AI-Diagnostics Workflow nutzen möchtest:
```
Name: ANTHROPIC_API_KEY
Value: [Generiere hier: https://console.anthropic.com/account/keys]
```

### 3. Commit & Push

```bash
git add .github/workflows/ tests/ CI_CD_SETUP.md
git commit -m "chore: Add complete CI/CD pipeline with AI diagnostics"
git push
```

## 📊 Pipeline-Flow

```
git push to main
    ↓
[Unit Tests] - Testet Python Code
    ↓
[Docker Test] - Baut Image, testet Container, Security Scan
    ↓
[Docker Push] - Pushed zu Docker Hub
    ↓
✅ Done!

Falls irgendwo Fehler:
    ↓
[Auto-Fix] - Versucht automatische Fixes
    ↓
[AI Diagnostics] - Claude AI analysiert & generiert Fixes
    ↓
Pull Request mit Fixes
```

## 🔍 Workflows im Detail

| Workflow | Trigger | Zeit | Aktion |
|----------|---------|------|--------|
| Unit Tests | Jeder Push/PR | 2-3 min | Testet Python Code |
| Docker Test | Jeder Push/PR | 3-5 min | Baut & testet Image |
| Docker Push | Push zu main, Tags | 5-8 min | Pushed zu Docker Hub |
| Dependabot | Montag 3 Uhr | - | Prüft Updates |
| Auto-Fix | Bei Fehlern | 2-3 min | Versucht Fixes |
| AI Diagnostics | Bei Fehlern | 2-3 min | Claude AI Analyse |

## ✅ Test-Beispiel: Erste Pipeline

**Local:**
```bash
git checkout -b test/ci-pipeline
echo "Test" >> README.md
git add .
git commit -m "test: trigger pipeline"
git push -u origin test/ci-pipeline
```

**In GitHub:**
1. Gehe zu **Actions** Tab
2. Du siehst die Workflows starten:
   - 🟡 Unit Tests (läuft...)
   - 🟡 Docker Test Build (läuft...)
3. Warte bis beide grün sind ✅

**Nach erfolgreichem Test:**
```bash
git checkout main
git merge test/ci-pipeline
git push
```

Jetzt wird automatisch zu Docker Hub gepusht! 🎉

## 🐛 Häufige Probleme

### "Docker push failed - auth error"
**Lösung:**
- Checke DOCKERHUB_USERNAME und DOCKERHUB_TOKEN
- Token muss Personal Access Token sein, nicht Passwort
- Token hat keine Whitespace/Newlines

### "Test failed - requirements conflict"
**Lösung:**
1. Workflow erstellt automatisch PR mit Fixes
2. Review und merge den Auto-Fix PR
3. Workflow läuft neu

### "Health check timeout"
**Lösung:**
1. Check die Logs in der Workflow
2. AI Diagnostics erstellt Issue
3. Meistens: Startup dauert länger
   - Ändere in docker-compose.yml:
   ```yaml
   start_period: 60s  # Statt 40s
   ```

## 📈 Best Practices

✅ **DO:**
- Tag releases: `git tag v1.0.0 && git push --tags`
- Review Dependabot PRs wöchentlich
- Check Security Tab in GitHub für Vulnerabilities
- Merge Auto-Fix PRs wenn Tests grün sind

❌ **DON'T:**
- Commit zu main ohne Push (skipped Workflows)
- Änder docker-compose.yml im Produktions-Container
- Ignoriere Trivy Security Warnings
- Merge abhängig PRs, bis alle unabhängig grün sind

## 🔗 Nützliche Links

- [.github/WORKFLOWS.md](.github/WORKFLOWS.md) - Detaillierte Dokumentation
- [tests/test_api.py](tests/test_api.py) - Unit Tests
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Docker Hub CLI](https://docs.docker.com/docker-hub/cli-tool/)

## 🎯 Nächste Schritte

1. ✅ Alle Secrets hinzufügen
2. ✅ Ersten Push machen
3. ✅ Workflows in Actions Tab beobachten
4. ✅ Sicherheits-Updates mit Dependabot reviewen
5. ✅ Neue Features entwickeln & automatisch deployen

---

**Fragen?** Schau in [.github/WORKFLOWS.md](.github/WORKFLOWS.md) oder erstelle ein Issue! 🚀
