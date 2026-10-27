# Fix for Issue #891: Duplicate source files in MongoDB

**Issue:** [IDSIA/sacred#891](https://github.com/IDSIA/sacred/issues/891) (reported by Kwentar, assigned to adriennie)
**Branch:** `issue-891`
**Commit:** `94a6675`

## Summary

Sacred's `MongoObserver` stored a new copy of every source file on every run, even when the file had not changed. With PyMongo 4 this happened every time. The fix is a one-line change that stores the file's MD5 checksum when the file is uploaded, so later runs can find and reuse the stored copy.

## Background

Sacred records experiments. For each run it saves the experiment's **source files** (the Python code that was run) so the run can be reproduced later. The `MongoObserver` saves these files in **GridFS**, MongoDB's storage for files.

To avoid storing the same file twice, Sacred first searches GridFS for a file with the same **path** and the same **MD5 checksum** (a fingerprint of the file's contents). It reuses that file if it finds one, and uploads a new copy if it doesn't.

## The problem

In `sacred/observers/mongo.py`, `save_sources()` looked up files by `md5`:

```python
file = self.fs.find_one({"filename": abs_path, "md5": md5})
```

but uploaded them **without** an `md5` field:

```python
_id = self.fs.put(f, filename=abs_path)
```

PyMongo 3 added the `md5` field to every GridFS upload automatically, so this worked. **PyMongo 4 stopped doing that** (see the [PyMongo 4 migration guide](https://pymongo.readthedocs.io/en/4.0/migrate-to-pymongo4.html)), so applications now have to store it themselves. Because Sacred didn't, the lookup never matched:

1. Run A uploads `train.py` (no `md5` stored).
2. Run B uses the same, unchanged `train.py`.
3. The lookup for `filename + md5` finds nothing.
4. Sacred uploads another copy. This repeats on every run.

**Impact:** database storage grows and upload time increases with every run. Experiment results are **not** affected.

## The fix

`save_sources()` already has the file's checksum, so the upload now stores it:

```python
# sacred/observers/mongo.py, save_sources()
_id = self.fs.put(f, filename=abs_path, md5=md5)
```

Now the field the lookup searches for actually exists, and unchanged files are reused. The change also works with PyMongo 3, where the field just matches the value PyMongo computes itself.

## Tests added

Two regression tests in `tests/test_observers/test_mongo_observer.py`:

| Test | What it checks |
|---|---|
| `test_mongo_observer_save_sources_reuses_unchanged_file` | Saving the same unchanged file twice returns the **same** GridFS ID, stores only **one** copy, and the stored file has the correct `md5`. |
| `test_mongo_observer_save_sources_uploads_changed_file` | After the file is edited, saving it returns a **new** ID and both versions are stored. |

The first test **failed before the fix** (the second save created a new ID) and **passes after it**, which confirms it catches the bug.

## Verification

| Check | Result |
|---|---|
| Mongo observer tests (Python 3.9, pymongo 4.8, mongomock 4.3) | 25 passed |
| Full test suite, Python 3.9, CI's pinned dependencies | 749 passed |
| `black` and `flake8` (repo's pre-commit config) | Passed |
| `tox -e setup` | Passed |
| Conflicts with upstream `master` | None |

Note: the Mongo test file is skipped on Python 3.10 and newer (mongomock limitation), so these tests run on Python 3.8 and 3.9 in CI.

## Scope: what this fix does not change

- **`resource_event()`**: it has a similar MD5 lookup, but resources are handled differently (they are recorded, not uploaded). It was left unchanged on purpose and can be handled in a separate change.
- **Existing duplicates**: copies already stored in a database are not removed. The fix only prevents new duplicates.
- **Two runs at the same moment**: if two processes upload the same new file at exactly the same time, both may still store it. That was true before as well.

## Known CI issue (not caused by this fix)

Upstream CI currently fails on **every** PR, including this one, for two reasons unrelated to this change:

1. **`pkg_resources` missing.** CI installs the newest setuptools (version 81 or later), which no longer includes `pkg_resources`. Sacred imports it in `sacred/dependencies.py`, so pytest stops at startup before any test runs. With `setuptools<81` installed, all tests pass.
2. **One Python 3.11 test.** `test_tinydb_observer.py::test_serialisation_of_pandas_dataframe` fails with newer pandas. It fails the same way on a clean `master`.

The last passing `master` build was on 2025-10-22. An upstream PR to replace `pkg_resources` is already open.

## Next steps

1. Push the `issue-891` branch to the fork.
2. Open a PR to `IDSIA/sacred` with "Fixes #891" in the description, noting the CI issue above.
3. A maintainer approves the CI run, reviews and merges. Issue #891 closes on merge.
