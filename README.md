# GitHub Repository Traffic Scraper

This scraper collects traffic data, commit statistics, and other metrics from all your GitHub repositories. It collects data from exactly 7 days ago (a single day snapshot) and stores it in a historical database that accumulates over time.

## Features

- **Traffic Data**: Views and unique visitors, clones and unique cloners
- **Commit Statistics**: Number of commits, additions, deletions, and net change for the target date
- **Repository Metrics**: Stars, forks, watchers, open issues, language
- **Historical Tracking**: Each run appends data for the target date, building a historical record
- **Private Repo Support**: Works with both public and private repositories

## Setup

### 1. Create a GitHub Personal Access Token (PAT)

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Direct link: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Give it a descriptive name (e.g., "Repo Traffic Scraper")
4. Set expiration (recommended: 90 days or custom)
5. Select the following scopes:
   - ✅ `repo` (Full control of private repositories) - Required for private repos
   - ✅ `public_repo` (Access public repositories) - Required for public repos
6. Click "Generate token"
7. **Copy the token immediately** (you won't be able to see it again!)

### 2. Configure the Token

You have two options:

#### Option A: Environment Variable (Recommended)
```powershell
$env:GITHUB_TOKEN = "your_token_here"
```

#### Option B: Config File
Create a `config.json` file in the project directory:
```json
{
  "github_token": "your_token_here"
}
```

**Important**: Add `config.json` to `.gitignore` to avoid committing your token!

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

## Usage

### Basic Usage

Run the scraper to collect data from 7 days ago:

```powershell
python github_repo_scraper.py
```

### Custom Date

To collect data from a different number of days ago, modify the `days_ago` parameter in the `main()` function or pass it as needed.

## Output

The scraper creates two files:

1. **`github_repo_data.json`**: Complete historical data in JSON format
   - Structure: `{"historical_data": [...], "last_updated": "..."}`
   - Each entry contains full repository statistics for a specific date

2. **`github_repo_data.csv`**: Historical data in CSV format for easy analysis
   - Each row represents one repository for one date
   - Perfect for importing into Excel, Google Sheets, or data analysis tools

## Data Collected

For each repository and date, the scraper collects:

- **Repository Info**: Name, owner, privacy status, language, description
- **Traffic**: Views (total and unique), clones (total and unique)
- **Commits**: Count, additions, deletions, net change
- **Metrics**: Stars, forks, watchers, open issues
- **Metadata**: Date, scraped timestamp

## How It Works

1. The scraper calculates the target date (7 days ago by default)
2. For each repository, it:
   - Fetches traffic data from the GitHub API (last 14 days available)
   - Extracts data for the specific target date
   - Gets all commits made on that specific day
   - Calculates additions and deletions from commit stats
3. Appends the data to the historical record
4. If data for that date already exists, it updates it

## Scheduling (Optional)

To run this daily automatically, you can:

### Windows Task Scheduler
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger to "Daily"
4. Set action to run: `python C:\path\to\github_repo_scraper.py`

### Or use a cron job (if using WSL)
```bash
0 0 * * * cd /path/to/scraper && python github_repo_scraper.py
```

## Notes

- GitHub's traffic API only provides data for the last 14 days
- The scraper collects data from exactly 7 days ago to ensure data is complete
- Private repos with no traffic will still be tracked for commit counts
- The historical database grows over time - consider archiving old data periodically

## Troubleshooting

**Error: "GitHub token not found!"**
- Make sure you've set the `GITHUB_TOKEN` environment variable or created `config.json`

**Error: "Bad credentials"**
- Your PAT may have expired or been revoked
- Check that the token has the correct scopes (`repo` and/or `public_repo`)

**Error: "Not found" for private repos**
- Ensure your PAT has the `repo` scope enabled
- Verify you have access to the repository

**No traffic data for some repos**
- Traffic data is only available for repositories you own or have admin access to
- Some repos may genuinely have no traffic for that day

