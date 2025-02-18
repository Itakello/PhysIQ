# GitHub Copilot Custom Instructions

## Libraries and Their Usage
1. `pathlib`: for file system path management (files, folders, etc.).
2. `loguru`: for logging and diagnostics.
3. `tqdm`: for tracking progress in loops or long-running operations.
4. `pytest`: for writing and running unit tests.
5. `weave`: for tracking LLM evaluations.
6. `liteLLM`: for calling LLMs.
7. `streamlit`: for building interactive data applications and dashboards with minimal code.
8. `fastapi`: for creating high-performance, type-safe REST APIs with automatic OpenAPI documentation.
9. `pydantic`: 

## Code-generation instructions
1. Always write concise, maintainable Python code.
2. Emphasize object-oriented principles: encapsulation, modularization, and single-responsibility functions.
3. Use descriptive variable and function names.
4. Keep the project structure logical and organized.
5. Use classes and methods to encapsulate functionality.
6. Include docstrings in modules, classes, and functions.
7. Use context managers (`with` statements) to manage resources.
8. Use base Python types (`dict`, `list`, `tuple`) for type hinting instead of `typing`.
9. Avoid `Optional` and `Union`; use `| None` and the `|` operator for unions.
10. In classes, place public methods above private ones (`_method`).
11. Write code with error handling (`try/except`) and input validation.
12. Organize dependencies in `requirements.txt` and manage them with virtual environments.
13. Integrate code generation seamlessly into existing workflows and ensure clarity.

## Test-generation instructions
1. Write unit tests using frameworks like `unittest` or `pytest`.
2. Maintain high test coverage for critical components.
3. Automate test execution with continuous integration.
4. Use meaningful, isolated test methods for clarity.
5. Verify error handling and edge cases in tests.

## Code review instructions
1. Ensure each function or method has a single responsibility.
2. Check for consistent naming and logical organization.
3. Verify docstring accuracy and completeness.
4. Confirm proper handling of errors and exceptions.
5. Check that logging with `loguru` is present where needed.
6. Ensure code is modular, with minimal duplication.
7. Review for secure handling of data and proper input validation.

## Commit message generation instructions
1. Keep commit messages concise and descriptive.
2. Reference the purpose of changes (e.g., feature, fix, refactor).
3. Provide meaningful context for each commit.
4. Include only essential details.
5. Use an active, imperative tone (e.g., "Add new feature" rather than "Added").
6. Emphasize clarity, ensuring future reviewers understand the purpose of the change.