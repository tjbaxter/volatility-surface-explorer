# Deployment Checklist

## Local Verification

- [ ] Create and activate a virtual environment
- [ ] Install dependencies from `requirements.txt`
- [ ] Run module smoke tests:
  - [ ] `python -m src.data_loader`
  - [ ] `python -m src.greeks`
  - [ ] `python -m src.surface_builder`
  - [ ] `python -m src.strategy`
- [ ] Run tests: `pytest tests/test_strategy.py -v`
- [ ] Start app: `streamlit run app.py`

## Runtime Checks

- [ ] App loads without import/runtime errors
- [ ] Surface tab renders with available data
- [ ] Greeks tab computes and plots values
- [ ] Backtest tab executes and returns metrics
- [ ] No obvious UI regressions

## Cloud Deployment (Optional)

- [ ] Push current code to GitHub
- [ ] Configure host with `app.py` as entry point
- [ ] Verify environment has required Python version
- [ ] Validate logs for dependency/data issues
- [ ] Re-run basic functionality checks after deploy

## Maintenance

- [ ] Periodically review dependency updates
- [ ] Re-check assumptions in transaction cost and risk settings
- [ ] Keep a changelog for model or strategy behavior changes
