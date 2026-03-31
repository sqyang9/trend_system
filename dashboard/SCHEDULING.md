# Scheduling

## Recommended cadence

- Run after each `4h` bar close.
- Practical schedule:
  - `00:05`
  - `04:05`
  - `08:05`
  - `12:05`
  - `16:05`
  - `20:05`

## launchd

Use the template files in this folder:

- `launchd/com.trend-system.mainline-dashboard.plist.template`
- `install_launchd.command`

The install script writes a user-level LaunchAgent and loads it.

## Fallback

- If the machine was asleep or the screen was closed, rerun manually with:
  - `dashboard/run_mainline_dashboard.command`
- The dashboard is in strict-refresh mode:
  - it must update data successfully before generating a signal
  - if refresh fails, it should report an error instead of using stale local data
