# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Code analysis moved from SonarQube Cloud Automatic Analysis to a scan run from
  CI, with a coverage report attached. Automatic Analysis cannot import coverage,
  so the dashboard reported none for a suite that in fact covers 96% of the
  package. Configuration moved from `.sonarcloud.properties` to
  `sonar-project.properties` accordingly; the latter also supports
  `sonar.issue.ignore.multicriteria`, so known false positives are now recorded
  in the repository and reviewable in a diff instead of marked won't-fix in the
  dashboard.

## [0.1.0] - 2026-08-18

First release published to PyPI. Earlier `0.0.x` tags were never published, and
their build metadata always resolved to `0.0.0` (see Fixed), so `0.1.0` is the
first version with a correct, installable distribution.

### Fixed

- **Packaging: no more stray `__init__.py` in `site-packages`.** `src`-layout
  auto-discovery treated `src/` as the package root, so `src/__init__.py` was
  installed as a bare `__init__.py` at the top level of `site-packages`, where it
  collided with any other package doing the same and was removed by
  `pip uninstall`. The module now lives in a real `src/time_executioner/` package.
- **Packaging: the version no longer resolves to `0.0.0`.** `dynamic = ["version"]`
  had no corresponding `[tool.setuptools.dynamic]` section, so every build
  silently produced `0.0.0` while `__init__.py` claimed `0.0.2`. Version is now
  read from `time_executioner.__version__` as a single source of truth.
- **Python 3.16 compatibility.** Replaced `asyncio.iscoroutinefunction()` with
  `inspect.iscoroutinefunction()`; the former is deprecated and scheduled for
  removal in Python 3.16. The test suite's blanket `-W ignore::DeprecationWarning`
  had been hiding this.
- Corrected a typo in the `Homepage` project URL.
- The test suite no longer leaks a `set_logger()` call into the process-wide
  default, which previously persisted past the run that made it.

### Added

- **`logger=` argument** on `TimeExecutioner.log()` and `TimeExecutioner.time()`,
  for overriding the logger per use. `set_logger()` mutates process-wide state, so
  two consumers in one process previously had no way to avoid clobbering each
  other.
- `TimeExecutioner.reset_logger()`, restoring the built-in default logger.
- **`py.typed` marker.** The library was fully annotated but shipped no PEP 561
  marker, so type checkers in consuming projects silently ignored every
  annotation. Type information is now published.
- A `dev` extra (`pip install -e '.[dev]'`) replacing `requirements.txt`.
- CI now tests on Python 3.11–3.14, runs the `pre-commit` suite, and builds the
  distribution to verify it is installable, importable, correctly versioned, and
  free of stray top-level files.
- A tag-triggered PyPI publish workflow using trusted publishing.
- PyPI keywords and classifiers, including `Typing :: Typed`.
- This changelog and `CONTRIBUTING.md`.
- All GitHub Actions references pinned to commit SHAs rather than mutable tags,
  with Dependabot configured to keep them current.
- `requirements-publish.txt`, a hash-pinned build toolchain for the release
  workflow. The publish job previously installed the full unpinned dev extra
  before building the artifact it uploads to PyPI, so a compromised release of
  any build-time dependency could have altered what users receive. It now
  installs only `build` and `twine`, with `--require-hashes`.
- Explicit least-privilege `permissions` declared per job on both workflows.
- `pylock.toml`, a PEP 751 lock file pinning every development dependency to an
  exact version and hash, installed by pip in CI so contributors and CI run
  identical tooling.

### Changed

- `__version__` is now a string attribute rather than a zero-argument function.
  **Breaking** for anyone who called `time_executioner.__version__()`; use
  `time_executioner.__version__` instead.
- The default logger name moved from `time_executioner` to
  `time_executioner._core`, following the module split. Configuration applied to
  the `time_executioner` logger still applies, since child loggers propagate to
  their parent.
- Tests import the installed `time_executioner` package rather than the in-tree
  `src.time_executioner` path, so they exercise the built artifact.
- pytest configuration moved from `pytest.ini` into `pyproject.toml`, which also
  removes an inert `[tool.pytest.ini_options]` block that `pytest.ini` never read.
  `DeprecationWarning` is now an error in the test suite.

[Unreleased]: https://github.com/Rapid-Medical/time_executioner/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Rapid-Medical/time_executioner/releases/tag/v0.1.0
