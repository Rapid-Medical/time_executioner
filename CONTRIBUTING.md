# Contributing

Thanks for your interest in improving Time Executioner.

## Getting set up

Requires Python 3.11 or newer.

```bash
git clone https://github.com/Rapid-Medical/time_executioner.git
cd time_executioner
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
pre-commit install
```

The editable install matters: the tests import the installed `time_executioner`
package, not the `src/` tree. Running `pytest` without installing first will fail
with `ModuleNotFoundError`. This is deliberate — it means the suite exercises the
same import path your users get.

## Running the checks

```bash
pytest                       # tests
pre-commit run --all-files   # black, isort, flake8, bandit, mypy
```

`DeprecationWarning` is configured as an error in the test suite. If a dependency
starts emitting one you cannot act on, add a targeted `ignore` entry to
`filterwarnings` in `pyproject.toml` rather than widening it back to a blanket
ignore.

## Verifying the distribution

Packaging bugs are invisible to a source-tree test run, so check the built
artifact when you touch `pyproject.toml` or move files:

```bash
python -m build
python -m zipfile --list dist/*.whl
```

Everything in the wheel should sit under `time_executioner/` or
`time_executioner-*.dist-info/`. A file at the top level would be installed
loose into the user's `site-packages`. CI enforces this.

## Pull requests

- Branch off `main`.
- Add tests for behaviour changes.
- Add a `## [Unreleased]` entry to `CHANGELOG.md`.
- Keep the public API annotated; the package ships a `py.typed` marker, so
  consumers' type checkers rely on these annotations being accurate.

## Releasing

Maintainers only:

1. Bump `__version__` in `src/time_executioner/__init__.py`.
2. Move `## [Unreleased]` entries in `CHANGELOG.md` under the new version.
3. Commit, then tag and push:

```bash
git tag v0.1.0 && git push origin v0.1.0
```

The publish workflow verifies the tag matches `__version__`, then uploads to
PyPI via trusted publishing. Version numbers cannot be reused on PyPI, so the
tag/version check is a hard gate.

That workflow builds with only `build` and `twine`, installed from
`requirements-publish.txt` with `--require-hashes`, rather than the dev extra:
anything running during the release build can alter the artifact that reaches
users. If you need to change that toolchain, edit `requirements-publish.in` and
regenerate — the command is in the generated file's header.
