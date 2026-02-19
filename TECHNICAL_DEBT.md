# Technical Debt & Refactoring

This document tracks technical debt, known issues, and planned refactoring tasks.

## 🚧 High Priority

### Backend
- [x] **Database**: Add migrations (Alembic) management.
- [ ] **Security**: API Key validation is basic; consider JWT or OAuth2.
- [x] **Testing**: Increase coverage for `backend/api/deps.py` and `backend/main.py` (currently < 80%).

### Frontend
- [ ] **Types**: Migrate to TypeScript for better type safety.
- [ ] **Testing**: Add E2E tests (Playwright/Cypress).

## ⚠️ Medium Priority

### Code Quality
- [x] **Logging**: Standardize log formats across all services (JSON preferred).
- [x] **Config**: Unify configuration management (currently split between env vars and constants).

### Documentation
- [x] **API**: Add interactive redoc/swagger documentation links in README.

## 📉 Low Priority / Future
- [ ] **Performance**: Redis caching for frequent analysis requests.
- [ ] **Deployment**: Add Kubernetes manifests.
