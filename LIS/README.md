# LIS Folder Summary (Cleaned)

This folder is now standardized for HMS integration work.

## Kept

- `LIS_CPH_Code/`  
  Primary source for LIS analyzer connectors (Python).
- `LIS_Protocol/`  
  Vendor/interface protocol documents (PDF/PPT/XLSX).
- `LIS_20231202.xlsx`  
  Existing mapping/config workbook.

## Removed

- Duplicate source tree: `cph-lis-master/cph-lis-master`  
  It was byte-identical to `LIS_CPH_Code` for all common files.
- Generated/IDE artifacts:
  - `__pycache__/`
  - `*.pyc`
  - `build/`
  - `dist/`
  - `.idea/`
  - `.DS_Store`

## Next Engineering Goal

Migrate from many standalone scripts to one service-oriented LIS bridge integrated with HMS backend.

See: `docs/lis-integration-plan.md`
