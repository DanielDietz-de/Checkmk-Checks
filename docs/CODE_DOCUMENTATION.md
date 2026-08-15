# Code-level documentation policy

Every tracked named function, asynchronous function, and class must carry a
human-readable docstring that explains its purpose. The repository also
requires adjacent purpose comments for tracked PowerShell, shell, and PHP
function declarations.

The rule applies to production code, tests, CI/release tooling, and retained
reference or archived source. Trivial helpers are not exempt: a future
maintainer must be able to understand why a callable exists without having to
reverse-engineer its implementation first.

`python tools/ci/check_function_documentation.py` enforces the policy in the
repository guard. Generated documentation is a one-time normalization aid;
new and changed code should be documented intentionally by its author.
