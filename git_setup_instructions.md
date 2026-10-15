# Git Setup Instructions

## Prerequisites
Make sure you have Git installed:
```bash
git --version
```

## Setup Commands
Run these commands in your terminal:

```bash
cd /home/pj-mcnerney/ai/animation-agent
git status
git init
git add .
git commit -m "Update pipeline"
```

## If You Want to Push to GitHub
1. Create a new repository on GitHub.com
2. Then run:
```bash
git remote add origin https://github.com/YOUR_USERNAME/animation-agent.git
git branch -M main
git push -u origin main
```

## Alternative: Using GitHub CLI
If you have GitHub CLI installed:
```bash
gh repo create animation-agent --public --description "Multi-stage automation pipeline for AI animation using local LLMs, audio generation, and Cartoon Animator"
git push -u origin main
```

## Verify Setup
After pushing, verify your repository:
```bash
git remote -v
git log --oneline -5
```