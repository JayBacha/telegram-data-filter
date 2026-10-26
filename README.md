# Telegram Number Filter V2

## Features
- Upload CSV, XLSX, or TXT phone lists.
- Validate basic Indian mobile number format (+91).
- Detect duplicates.
- Optionally upload an authorized CSV/XLSX status file and match it to the phone list.
- Filter status labels and last-seen categories.
- Export separate CSV reports and a combined Excel workbook.

## Important limitation
This app does not query Telegram, discover accounts from phone numbers, or fetch last-seen information. It matches the phone list against a status file you are authorized to use. Missing or unclear data stays Unknown. Status labels are not independently verified.

## Example authorized status file
Use columns such as `phone`, `telegram_status`, and `last_seen`.

| phone | telegram_status | last_seen |
|---|---|---|
| +919876543210 | Active | 2026-10-26T15:30:00Z |
| 9876543211 | Unknown | recently |
| +919876543212 | No account | |

Recognized active values: `Active`, `exists`, `account exists`, `telegram account exists`, `confirmed`.
Recognized no-account-indicated values: `No account`, `not found`, `no telegram`, `no telegram account`, `not registered`, `inactive`.
Other values become Unknown.

Use ISO timestamps with timezone, e.g. `2026-10-26T15:30:00Z`. Labels such as `recently`, `within a week`, `within a month`, `a long time ago`, `hidden`, and `private` remain approximate and cannot be assigned to exact 24-hour/3-day/7-day windows.

## Deploy without installing Python locally
1. Extract this ZIP.
2. Create a GitHub repository.
3. Upload `app.py`, `requirements.txt`, and optionally `README.md` to the repository root.
4. Open https://share.streamlit.io/ and sign in with GitHub.
5. Create an app, select the repository, branch `main`, and main file `app.py`.
6. Deploy.

Do not upload real phone lists to GitHub. The app has no login or permanent database; do not use a public deployment for confidential records without adding appropriate access protection.
