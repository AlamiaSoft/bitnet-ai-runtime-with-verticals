# Roadmap: Final Architectural Proof & Productization Strategy

## 1. Final Architectural Proof (Immediate Priority on Resume)
Before adding any new runtime features, execute the rigorous architectural proof:

### A. True External-Plugin Test
- [ ] Install runtime alone in a clean virtual environment (`pip install .` or `pip install bitnet-runtime`).
- [ ] Confirm the runtime CLI, API server, and ReAct agent run with **zero `verticals/` package present**.
- [ ] Install one vertical independently as an external package.
- [ ] Confirm dynamic discovery works seamlessly without modifying any core runtime code.

### B. Adversarial Security Test
- [ ] Test advanced shell bypass techniques beyond standard dangerous strings (e.g. environment variable execution, encoding tricks, subshell wrapping, symlink attacks).
- [ ] Verify `PolicyDecision.ASK` actually enforces an interactive decision boundary / confirmation modal rather than merely existing as an enum.

### C. Packaging / Release Test
- [ ] Build the standalone `bitnet-runtime` package wheel.
- [ ] Build vertical package wheels (`bitnet-vertical-employee`, etc.).
- [ ] Test installation and end-to-end execution in clean environments.
- [ ] Test the low-end / high-end release artifacts.
- [ ] **Freeze Architecture**.

---

## 2. Productization & Commercial Strategy (Next Phase Discussion)
Following the architectural freeze, transition focus from runtime engineering to commercial productization:

```
BitNet Runtime ??? Plugin Ecosystem ??? Vertical Packages ??? Standalone Commercial Products
```

### Strategic Decisions:
1. **Core Distribution Model**: Determine what stays open-source/free vs. what becomes proprietary / paid.
2. **Vertical Commercial Viability**: Evaluate and select which of the 5 built-in verticals have the highest market demand and PMF:
   - **AI Employee in a Box** (SMB CRM, Lead Triage, Morning Briefings)
   - **Personal Memory OS** (Local Offline Document & Note Recall)
   - **AI Computer Operator** (Desktop Automation & Repository Inspector)
   - **WhatsApp AI Employee** (Local Conversational Order & Appointment Assistant)
   - **AI QA Box** (Autonomous Crawler & Regression Checker)
3. **Packaging Strategy**: Package high-value verticals into turnkey, one-click installable desktop/server products for non-technical users.
