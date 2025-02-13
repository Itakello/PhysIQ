# GitHub Copilot Custom Instructions

## Libraries and Their Usage
1. `pathlib`: for file system path management (files, folders, etc.).
2. `loguru`: for logging and diagnostics.
3. `tqdm`: for tracking progress in loops or long-running operations.
4. `pytest`: for writing and running unit tests.
5. `weave`: for tracking LLM evaluations.
6. `liteLLM`: for calling LLMs.

## Code-generation instructions
1. Always write concise, maintainable Python code.
2. Emphasize object-oriented principles: encapsulation, modularization, and single-responsibility functions.
3. Use descriptive variable and function names.
4. Keep the project structure logical and organized.
5. Use classes and methods to encapsulate functionality.
6. Include docstrings in modules, classes, and functions.
7. Use context managers (`with` statements) to manage resources.
8. Prefer `dataclasses` for straightforward data structures.
9. Use base Python types (`dict`, `list`, `tuple`) for type hinting.
10. Avoid `Optional` and `Union`; use `| None` and the `|` operator for unions.
11. In classes, place public methods above private ones (`_method`).
12. Write code with error handling (`try/except`) and input validation.
13. For file system paths, use `pathlib`.
14. Keep track of progress in long-running operations with `tqdm`.
15. Organize dependencies in `requirements.txt` and manage them with virtual environments.
16. Integrate code generation seamlessly into existing workflows and ensure clarity.

## Test-generation instructions
1. Write unit tests using frameworks like `unittest` or `pytest`.
2. Maintain high test coverage for critical components.
3. Automate test execution with continuous integration.
4. Use meaningful, isolated test methods for clarity.
5. Incorporate `tqdm` for progress monitoring when needed.
6. Verify error handling and edge cases in tests.

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