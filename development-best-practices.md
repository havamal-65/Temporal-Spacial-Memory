# Development Best Practices & Rules

## 6. Documentation & Knowledge Sharing
- **Document as you go:** Write concise docstrings, comments, and high-level documentation (e.g., in `README.md` or `docs/`). Focus on the "why" and "how," not just the "what."
- **Update documentation with code changes:** Whenever you refactor or add features, update related documentation to keep it accurate.
- **Maintain a "Getting Started" guide:** Keep a simple onboarding guide for new contributors (or your future self) to quickly set up and understand the project.

## 7. Code Review & Collaboration
- **Peer or "Rubber Duck" review:** Have someone else review your code, or explain it out loud/write a summary to catch hidden issues.
- **Small, focused commits:** Make each commit about a single logical change for easier history tracking and debugging.

## 8. Testing & Validation
- **Automate testing:** Write and maintain automated tests (unit, integration, end-to-end) to catch regressions and ensure reliability.
- **Test before you push:** Run tests locally before pushing to shared branches or deploying.
- **Use Continuous Integration (CI):** Set up CI tools to automatically run tests and checks on every push.

## 9. Refactoring & Technical Debt
- **Refactor regularly:** Clean up confusing or outdated code when you revisit it. Prefer "refactor before adding new features."
- **Track technical debt:** Keep a running list of known issues, TODOs, or areas needing improvement, and address them incrementally.

## 10. Consistency & Conventions
- **Consistent naming & structure:** Use consistent naming conventions, file organization, and formatting throughout the project.
- **Leverage linters & formatters:** Use tools to enforce style and catch simple errors automatically.

## 11. Tooling & Environment
- **Automate repetitive tasks:** Use scripts or task runners for setup, builds, tests, and deployment.
- **Version control everything:** Track not just code, but also configuration, documentation, and scripts in version control.

## 12. Personal Productivity
- **Leave "breadcrumbs" for yourself:** At the end of a work session, leave a short note (in code comments, a TODO, or a `notes.md`) about what you were doing and what's next.
- **Work in focused sessions:** Break work into small, manageable tasks. Use techniques like Pomodoro to maintain focus and avoid burnout.

## 13. Learning & Improvement
- **Review and reflect:** Regularly review what's working and what isn't in your workflow. Adjust your practices as needed.
- **Stay curious:** Keep learning about new tools, languages, and best practices. Share what you learn with your team or document it for future reference. 