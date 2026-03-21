# Roadmap: Daily Bank Transactions → Google Sheets

## Where you are now
- [x] Plaid connected to Dupaco
- [x] Access token saved to `.env`
- [ ] Everything below

---

## Step 1 — Set up Google Sheets API access (one-time, ~10 min)

1. Go to [console.cloud.google.com](https://console.cloud.google.com) 
- created this cloud project (plaid-connect-490822) DONE

3. Go to **APIs & Services → Enable APIs** → search and enable:
   - **Google Sheets API** DONE
   - **Google Drive API** DONE
4. Go to **APIs & Services → Credentials → Create Credentials → Service Account** DONE (lukeserviceaccount)
5. Click the service account you just created → **Keys tab → Add Key → JSON** 
   - This downloads a `.json` file — move it to your `bank/` folder and rename it `google_credentials.json`
   DPONE

6. Create a new Google Sheet at [sheets.google.com](https://sheets.google.com)
   - Name it "Bank Transactions" (or whatever you want)
   - Copy the Sheet ID from the URL: `https://docs.google.com/spreadsheets/d/16S-wja60k_2FHVTPZugDEm22jVtYGANOmns4X3DP1rU/edit?gid=0#gid=0`

   DONE
7. Open the sheet → click **Share** → paste in the service account email (looks like `bank-sync-bot@your-project.iam.gserviceaccount.com`) → give it **Editor** access
DONE
---

## Step 2 — Tell me to build the sync script

Once you've done Step 1, just say "build the sync script" and I'll create:

- `sync_to_sheets.py` — fetches last 30 days of transactions from Plaid and writes them to your Google Sheet (deduplicating so rows don't repeat)
- Updated `requirements.txt` with `gspread`
- A `GOOGLE_CREDENTIALS_FILE` and `GOOGLE_SHEET_ID` entry added to your `.env`

DONEEEE 
## Step 3 — Set up daily auto-run (Mac cron job, ~5 min)

Once the script works manually, I'll give you a one-liner to schedule it to run every day at a time you pick using `crontab`. No extra software needed — it's built into macOS.

Example: runs every day at 8am automatically, silently updates your sheet.

---

## End result

Your Google Sheet will:
- Have a header row: Date | Name | Merchant | Amount | Category | Channel | Pending
- Auto-update every morning with new transactions
- Deduplicate so you don't get double entries
- Always show the last 30 days (configurable)
