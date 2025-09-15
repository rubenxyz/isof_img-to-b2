# TODO

## Mirror Folder Structure in Output Directory

### Problem
Currently, all .txt link files are created flat in the output directory regardless of input folder structure. We need to preserve the input directory hierarchy in the output folder.

### Current Behavior
```
Input: USER-FILES/04.INPUT/folder1/subfolder/image.jpg
B2: b2://bucket/folder1/subfolder/image.jpg ✓ (already working)
Output: USER-FILES/05.OUTPUT/TIMESTAMP/image.txt ✗ (flat structure)
```

### Desired Behavior
```
Input: USER-FILES/04.INPUT/folder1/subfolder/image.jpg
B2: b2://bucket/folder1/subfolder/image.jpg ✓
Output: USER-FILES/05.OUTPUT/TIMESTAMP/folder1/subfolder/image.txt ✓
```

### Implementation Steps

- [x] **Step 1: Modify URL retrieval in generate_link_files()** ✅
  - Updated `get_actual_download_urls()` to return both URL and relative path
  - Added recursive flag to B2 ls command to get all files in subdirectories
  - Returns list of tuples: (url, relative_path)
  - Added filtering to skip directory entries

- [x] **Step 2: Update generate_link_files() function** ✅
  - Modified to accept relative path information from URL retrieval
  - Extracts relative path from each file
  - Creates corresponding subdirectory structure in output folder
  - Places .txt file in the appropriate subdirectory

- [x] **Step 3: Modify fallback logic** ✅
  - Updated fallback method to preserve directory structure
  - Parses b2_key to extract relative path
  - Creates subdirectories before writing text files

- [x] **Step 4: Handle edge cases** ✅
  - Implemented Path.mkdir(parents=True, exist_ok=True) for all subdirectories
  - Handles files at root level (no subdirectory)
  - Preserves folder structure with special characters

- [x] **Step 5: Testing** ✅
  - Tested with folder1/, folder2/, folder3/ containing images
  - Verified subdirectories are created in output
  - Confirmed text files are placed in correct subdirectories
  - Validated URLs contain correct folder paths







## Refactoring Tasks

### High Priority - Long Method Refactoring ✅

- [x] **Refactor `sync_operation()` in src/sync.py**
  - [x] Extract `_prepare_sync_command()` method for building sync command with exclusions
  - [x] Extract `_handle_sync_error()` method for error handling and report generation
  - [x] Extract `_generate_sync_outputs()` method for output file generation
  - [x] Extract `_log_sync_summary()` method for summary logging

- [x] **Refactor `clean_operation()` in src/sync.py**
  - [x] Extract `_verify_bucket_access()` method for bucket validation
  - [x] Extract `_get_user_confirmation()` method for user prompt logic
  - [x] Extract `_execute_clean_command()` method for actual deletion
  - [x] Extract `_cleanup_unfinished_files()` method for large file cleanup

### High Priority - Dead Code Removal ✅

- [x] **Remove unused functions from src/utils.py**
  - [x] Delete `get_supported_files()` function (lines 340-351)
  - [x] Delete `validate_file_size()` function (lines 327-337)
  - [x] Remove unused `import time` (line 6)

- [x] **Clean up src/config.py**
  - [x] Remove unused `TEMP_DIR` property (line 42)
  - [x] Remove unused `import os` (line 3)

### High Priority - Code Duplication ✅

- [x] **Fix duplicate code in `generate_link_files()` in src/utils.py**
  - [x] Extract common link file creation logic into `_create_link_file()` method
  - [x] Eliminate 30+ lines of duplicated code between main and fallback paths

- [x] **Extract duplicate subdirectory creation in src/utils.py**
  - [x] Create `_ensure_subdirectory(output_dir, file_path)` method
  - [x] Replace duplicate code at lines 156-163 and 187-194

### Medium Priority - Pattern Refactoring ✅

- [x] **Refactor `parse_b2_sync_output()` in src/utils.py**
  - [x] Create dictionary of regex patterns and handlers
  - [x] Replace repetitive if-statements with pattern handler lookup
  - [x] Reduce method from 67 lines to ~30 lines (reduced to 40 lines)

- [ ] **Extract common B2 command patterns in src/sync.py**
  - [ ] Create `_execute_b2_command_with_validation()` wrapper method
  - [ ] Replace repeated command execution patterns

- [ ] **Consolidate environment validation in src/sync.py**
  - [ ] Extract duplicate validation code (lines 36-38 and 127-129)
  - [ ] Consider using decorator pattern for validation

### Medium Priority - Method Extraction

- [ ] **Refactor `generate_json_log()` in src/utils.py**
  - [ ] Extract statistics calculation into `_calculate_sync_statistics()` method
  - [ ] Simplify main method flow

- [x] **Create path helper in src/utils.py**
  - [x] Extract `_get_link_file_path()` for lines 169-173 and 197-201
  - [x] Eliminate repeated conditional logic

### Low Priority - Code Quality ✅

- [x] **Remove redundant imports**
  - [x] Remove duplicate `import re` inside function (src/utils.py line 123)

- [x] **Extract magic numbers to constants**
  - [x] Create `DEFAULT_TIMEOUT_SECONDS = 1800` in src/utils.py
  - [x] Create `BYTES_PER_GB` constant in src/config.py
  - [x] Move hardcoded endpoint "f003" to configuration (created DEFAULT_B2_ENDPOINT constant)

- [ ] **Optimize performance**
  - [ ] Change list comprehension to generator in src/sync.py line 157
  - [ ] Use: `sum(1 for line in stdout.split('\n') if line.strip() and not line.startswith('--'))`

### Testing Preparation

- [ ] **Create unit tests for refactored methods**
  - [ ] Test suite for extracted sync methods
  - [ ] Test suite for extracted utility methods
  - [ ] Test suite for path handling logic

## Cleanup Tasks from Cleanup Report

### High Priority - Delete Obsolete Directories ✅

- [x] **Remove old_project_folder**
  - [x] ~~Backup the folder first (just in case)~~
  - [x] Delete entire `/old_project_folder/` directory
  - [x] Verify removal of ~500+ obsolete files

- [x] **Clean up empty documentation**
  - [x] Delete `/docs/README.md` (0 bytes)
  - [x] Delete `/docs/api.md` (0 bytes)
  - [x] Delete `/docs/user_guide.md` (0 bytes)
  - [x] Remove `/docs/` directory if empty

- [x] **Remove empty test directory**
  - [x] Delete `/tests/__init__.py` (empty)
  - [x] Remove `/tests/` directory

### Medium Priority - Clean Empty Files ✅

- [x] **Remove unnecessary __init__.py files**
  - [x] Delete `/src/__init__.py` (empty, not needed for Python 3.3+)

### Low Priority - Code Cleanup ✅

- [x] **Fix minor issues in src/sync.py**
  - [x] Line 97: Change `tuple[int, str]` to `Tuple[int, int]` for consistency
  - [x] Line 191: Remove unused variables (cancel_stdout, cancel_stderr)

- [x] **Clean up src/config.py**
  - [x] Line 31: Convert to raw strings: `r".*\.DS_Store"`
  - [x] Remove unused `dry_run` property from DEFAULT_CONFIG

- [x] **Fix src/cli.py**
  - [x] Line 91: Remove unused variable `init_parser`

### Configuration Review ✅

- [x] **Review and clean configuration files**
  - [x] Verify if `.pre-commit-config.yaml` is used, delete if not (DELETED)
  - [x] Check if `.mcp.json` is needed (KEPT - actively used)
  - [ ] Update `pyproject.toml` dependencies (future task)

### TODO Management

- [ ] **Archive completed tasks**
  - [ ] Move completed refactoring tasks to a CHANGELOG or archive section
  - [ ] Keep only active/pending tasks visible

### ⛔ STOP HERE ⛔

### DO NOT IMPLEMENT ANYTHING BELOW THIS LINE WITHOUT EXPLICIT USER REQUEST


