# Documentation Index

Central Business Tool Hub - Complete Documentation Hub

---

## 🚀 Quick Start

New to the project? Start here:
1. [Developer Guide](DEVELOPER_GUIDE.md) - Setup & architecture overview
2. [Claude Code Instructions](CLAUDE.md) - AI-assisted development guide
3. [Ubuntu Server Installation](01_Ubuntu_Server_Installation_Guide.md) - Server setup

---

## 👨‍💻 For Developers

**Setup & Architecture:**
- [Developer Guide](DEVELOPER_GUIDE.md) - Complete development setup, architecture, coding standards
- [Claude Code Instructions](CLAUDE.md) - Guidelines for AI-assisted development with Claude

**Security & Best Practices:**
- [Security Guidelines](SECURITY.md) - Authentication, 2FA, rate limiting, security protocols
- [PostgreSQL Best Practices](POSTGRESQL_BEST_PRACTICES.md) - Database optimization & patterns

**Testing:**
- See `tests/` directory and [Developer Guide](DEVELOPER_GUIDE.md#testing)

---

## 🚢 For Deployment & DevOps

**Deployment Guides:**
- [Deployment Overview](DEPLOYMENT.md) - Main deployment guide with links to detailed configs
- [Ubuntu Server Installation](01_Ubuntu_Server_Installation_Guide.md) - VPS server setup from scratch
- See `../deployment/` directory for:
  - [Systemd Services](../deployment/README.md)
  - [DNS Setup](../deployment/DNS_SETUP.md)
  - [Backup Setup](../deployment/BACKUP_SETUP.md)
  - [SSH Key Setup](../deployment/SSH_KEY_SETUP.md)
  - [Git Token Setup](../deployment/GIT_TOKEN_SETUP.md)

**Migration & Database:**
- [Migration Status](MIGRATION_STATUS.md) - PostgreSQL migration tracking (v3.3.10+)
- [PostgreSQL Best Practices](POSTGRESQL_BEST_PRACTICES.md) - Database optimization

---

## 🔧 For Operations & Maintenance

**Daily Operations:**
- [Troubleshooting Guide](03_Troubleshooting_Guide.md) - Common issues & solutions
- [Maintenance Checklists](04_Wartungs_Checklisten.md) - Regular maintenance tasks

**User Manuals:**
- [My Calendar Anleitung](MY_CALENDAR_ANLEITUNG.md) - End-user guide for My Calendar feature

---

## 📊 Project Planning & Analytics

**Roadmap & Vision:**
- [Roadmap](ROADMAP.md) - Feature roadmap & future plans
- [Case Study](CASE_STUDY.md) - PostgreSQL migration case study (v3.3.10)

**Tracking & Analytics:**
- [Tracking Setup](TRACKING_SETUP.md) - Activity tracking configuration
- [N8N Automation Plan](N8N_AUTOMATION_PLAN.md) - Workflow automation integration

---

## 📁 Archive

Historical documentation:
- [Archive Directory](archive/) - Legacy docs & migration guides

---

## 🔗 External Resources

- **GitHub Repository:** [Business Tool Hub](https://github.com/your-org/business-hub)
- **Production Server:** http://91.98.192.233 (Hetzner VPS)
- **Tech Stack:** Flask 3.0, PostgreSQL, Gunicorn, Nginx, Systemd

---

## 📝 Documentation Standards

**File Naming:**
- Uppercase: `DOCUMENT_NAME.md` for primary docs
- Numbered: `01_Document_Name.md` for sequential guides
- Lowercase: `feature_guide.md` for feature-specific docs

**Cross-Referencing:**
- Use relative paths: `[Link](../other_dir/file.md)`
- Always check links after moving files

**Maintenance:**
- Keep INDEX.md updated when adding new docs
- Archive outdated docs to `archive/` directory
- Version numbers in doc titles when appropriate (e.g., "v3.3.10")

---

**Last Updated:** 2025-11-25 (v3.3.13 - Root directory reorganization)
