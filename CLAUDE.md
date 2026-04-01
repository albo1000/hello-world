# CLAUDE.md

This file provides guidance to AI assistants (Claude and others) working in this repository.

## Repository Overview

**Repository**: `albo1000/hello-world`
**Status**: Newly initialized — no source code has been added yet.

This repository is at its initial state. As the project evolves, this file should be updated to reflect the actual codebase structure, conventions, and workflows.

---

## Development Branch

All AI-driven development should target the designated feature branch for the active task. Do not push directly to `main` unless explicitly authorized.

---

## Git Workflow

### Commits
- Write clear, descriptive commit messages in the imperative mood (e.g., "Add user authentication module")
- Keep commits focused — one logical change per commit
- Always commit with a message body when the change is non-trivial

### Branching
- Feature branches: `feature/<short-description>`
- Bug fixes: `fix/<short-description>`
- Documentation: `docs/<short-description>`
- AI-generated work: `claude/<task-description>` (auto-assigned by the harness)

### Pushing
- Always use `git push -u origin <branch-name>` for new branches
- Do not force-push without explicit user authorization
- Do not push to `main` or `master` without explicit user authorization

---

## Working with This Codebase

### Before Making Changes
1. Read the relevant files before editing them
2. Understand existing patterns before introducing new ones
3. Prefer editing existing files over creating new ones

### Code Conventions (to be updated as the project grows)
- Keep functions small and focused
- Avoid premature abstractions — build for the current requirement, not hypothetical futures
- Do not add comments unless the logic is non-obvious
- Do not add error handling for scenarios that cannot happen

### Testing
- Run tests before committing when a test suite exists
- Do not mark tasks complete if tests are failing

---

## AI Assistant Instructions

### General Principles
- **Read before editing**: Always read a file before modifying it
- **Minimal footprint**: Only change what is necessary to accomplish the task
- **No speculative work**: Do not add features, refactor, or "improve" code beyond what was asked
- **No guessing**: If a required value is unknown, ask rather than assume

### Risky Operations (require explicit user confirmation)
- Deleting files or directories
- Force-pushing or resetting git history
- Modifying CI/CD pipelines
- Publishing or deploying to external services

### Pull Requests
- Do not create a pull request unless the user explicitly requests one
- When creating a PR, summarize all commits included — not just the latest

---

## Updating This File

This CLAUDE.md should be kept current. Update it when:
- A new language, framework, or major dependency is introduced
- Build, test, or lint commands are established
- Team or project-specific conventions are decided
- New CI/CD workflows are added

The goal is that any AI assistant (or new contributor) can read this file and immediately understand how to work effectively in this repository.
