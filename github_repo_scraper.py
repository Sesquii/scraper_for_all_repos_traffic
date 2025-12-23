"""
GitHub Repository Traffic and Statistics Scraper

This script scrapes traffic data, commit statistics, and other metrics
from all repositories for a given GitHub user/organization.
"""

import os
import json
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class GitHubScraper:
    """Scraper for GitHub repository data including traffic and commits."""
    
    def __init__(self, token: str, username: str = "Sesquii"):
        """
        Initialize the GitHub scraper.
        
        Args:
            token: GitHub Personal Access Token
            username: GitHub username or organization name
        """
        self.token = token
        self.username = username
        self.base_url = "https://api.github.com"
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy."""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update({
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Repo-Scraper"
        })
        return session
    
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make a GitHub API request with error handling."""
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")
            return None
    
    def get_all_repos(self) -> List[Dict]:
        """Get all repositories for the user/organization."""
        repos = []
        url = f"{self.base_url}/users/{self.username}/repos"
        page = 1
        per_page = 100
        
        while True:
            params = {"page": page, "per_page": per_page, "type": "all"}
            data = self._make_request(url, params)
            
            if not data or len(data) == 0:
                break
                
            repos.extend(data)
            
            # Check if there are more pages
            if len(data) < per_page:
                break
                
            page += 1
        
        print(f"Found {len(repos)} repositories")
        return repos
    
    def get_traffic_views(self, owner: str, repo: str) -> Optional[Dict]:
        """Get traffic views data for a repository."""
        url = f"{self.base_url}/repos/{owner}/{repo}/traffic/views"
        params = {"per": "day"}
        return self._make_request(url, params)
    
    def get_traffic_clones(self, owner: str, repo: str) -> Optional[Dict]:
        """Get traffic clones data for a repository."""
        url = f"{self.base_url}/repos/{owner}/{repo}/traffic/clones"
        params = {"per": "day"}
        return self._make_request(url, params)
    
    def get_traffic_for_date(self, traffic_data: Optional[Dict], target_date: str) -> Dict[str, int]:
        """Extract traffic data for a specific date from the API response."""
        result = {"count": 0, "uniques": 0}
        
        if traffic_data:
            # Check for views or clones array
            data_key = "views" if "views" in traffic_data else "clones"
            if data_key in traffic_data:
                for entry in traffic_data[data_key]:
                    entry_date = entry["timestamp"][:10]  # YYYY-MM-DD
                    if entry_date == target_date:
                        result["count"] = entry.get("count", 0)
                        result["uniques"] = entry.get("uniques", 0)
                        break
        
        return result
    
    def get_traffic_popular_paths(self, owner: str, repo: str) -> Optional[List[Dict]]:
        """Get popular paths for a repository."""
        url = f"{self.base_url}/repos/{owner}/{repo}/traffic/popular/paths"
        return self._make_request(url)
    
    def get_traffic_popular_referrers(self, owner: str, repo: str) -> Optional[List[Dict]]:
        """Get popular referrers for a repository."""
        url = f"{self.base_url}/repos/{owner}/{repo}/traffic/popular/referrers"
        return self._make_request(url)
    
    def get_commits(self, owner: str, repo: str, since: datetime, until: datetime) -> List[Dict]:
        """Get commits between two specific dates."""
        commits = []
        url = f"{self.base_url}/repos/{owner}/{repo}/commits"
        page = 1
        per_page = 100
        
        while True:
            params = {
                "page": page,
                "per_page": per_page,
                "since": since.isoformat(),
                "until": until.isoformat()
            }
            data = self._make_request(url, params)
            
            if not data or len(data) == 0:
                break
                
            commits.extend(data)
            
            if len(data) < per_page:
                break
                
            page += 1
        
        return commits
    
    def get_commit_stats(self, owner: str, repo: str, since: datetime, until: datetime) -> Dict[str, Any]:
        """Get commit statistics for a specific date range including additions and deletions."""
        commits = self.get_commits(owner, repo, since, until)
        
        total_additions = 0
        total_deletions = 0
        
        # Get detailed stats for each commit
        for commit in commits:
            sha = commit["sha"]
            commit_detail = self._make_request(
                f"{self.base_url}/repos/{owner}/{repo}/commits/{sha}"
            )
            if commit_detail and "stats" in commit_detail:
                total_additions += commit_detail["stats"].get("additions", 0)
                total_deletions += commit_detail["stats"].get("deletions", 0)
        
        return {
            "commits": len(commits),
            "additions": total_additions,
            "deletions": total_deletions,
            "net_change": total_additions - total_deletions
        }
    
    def get_repo_stats(self, repo: Dict, target_date: str) -> Dict[str, Any]:
        """
        Get comprehensive statistics for a repository for a specific date.
        
        Args:
            repo: Repository dictionary from GitHub API
            target_date: Target date in YYYY-MM-DD format (7 days ago)
        
        Returns:
            Dictionary with repository statistics for the target date
        """
        owner = repo["owner"]["login"]
        repo_name = repo["name"]
        
        print(f"Processing {owner}/{repo_name} for date {target_date}...")
        
        # Calculate start and end of target date (7 days ago)
        target_datetime = datetime.strptime(target_date, "%Y-%m-%d")
        since_datetime = target_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
        until_datetime = target_datetime.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Get traffic data (API returns last 14 days, we'll extract the specific date)
        views_data = self.get_traffic_views(owner, repo_name)
        clones_data = self.get_traffic_clones(owner, repo_name)
        
        # Extract data for the specific date
        views_for_date = self.get_traffic_for_date(views_data, target_date) if views_data else {"count": 0, "uniques": 0}
        clones_for_date = self.get_traffic_for_date(clones_data, target_date) if clones_data else {"count": 0, "uniques": 0}
        
        # Get commit statistics for that specific day
        commit_stats = self.get_commit_stats(owner, repo_name, since_datetime, until_datetime)
        
        # Compile all data for this specific date
        stats = {
            "date": target_date,
            "repository": {
                "name": repo_name,
                "full_name": repo["full_name"],
                "owner": owner,
                "private": repo.get("private", False),
                "description": repo.get("description"),
                "url": repo.get("html_url"),
                "language": repo.get("language"),
                "stargazers_count": repo.get("stargazers_count", 0),
                "forks_count": repo.get("forks_count", 0),
                "watchers_count": repo.get("watchers_count", 0),
                "open_issues_count": repo.get("open_issues_count", 0),
            },
            "traffic": {
                "views": views_for_date["count"],
                "views_uniques": views_for_date["uniques"],
                "clones": clones_for_date["count"],
                "clones_uniques": clones_for_date["uniques"]
            },
            "commits": commit_stats,
            "scraped_at": datetime.now().isoformat()
        }
        
        return stats
    
    def scrape_all_repos(self, days_ago: int = 7) -> List[Dict[str, Any]]:
        """
        Scrape all repositories for the user/organization for a specific date.
        
        Args:
            days_ago: Number of days ago to collect data for (default: 7)
        
        Returns:
            List of repository statistics dictionaries for the target date
        """
        # Calculate target date (7 days ago by default)
        target_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        print(f"Collecting data for date: {target_date} (7 days ago)")
        
        repos = self.get_all_repos()
        all_stats = []
        
        for repo in repos:
            try:
                stats = self.get_repo_stats(repo, target_date)
                all_stats.append(stats)
            except Exception as e:
                print(f"Error processing {repo['full_name']}: {e}")
                continue
        
        return all_stats
    
    def load_historical_data(self, filename: str = "github_repo_data.json") -> Dict[str, Any]:
        """Load existing historical data from JSON file."""
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load existing data: {e}")
                return {"historical_data": []}
        return {"historical_data": []}
    
    def save_to_json(self, data: List[Dict], filename: str = "github_repo_data.json"):
        """
        Save data to JSON file, appending to historical record.
        Each run adds a new entry for the target date.
        """
        # Load existing historical data
        historical = self.load_historical_data(filename)
        
        # Extract the date from the first entry (all entries should have the same date)
        if data and "date" in data[0]:
            target_date = data[0]["date"]
            
            # Check if we already have data for this date
            existing_dates = {entry.get("date") for entry in historical.get("historical_data", [])}
            
            if target_date in existing_dates:
                print(f"Warning: Data for {target_date} already exists. Updating...")
                # Remove old entries for this date
                historical["historical_data"] = [
                    entry for entry in historical.get("historical_data", [])
                    if entry.get("date") != target_date
                ]
            
            # Add new entries
            if "historical_data" not in historical:
                historical["historical_data"] = []
            
            historical["historical_data"].extend(data)
            historical["last_updated"] = datetime.now().isoformat()
            
            # Save to file
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(historical, f, indent=2, ensure_ascii=False)
            print(f"Data saved to {filename} (historical record)")
        else:
            # Fallback: save as-is if no date field
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Data saved to {filename}")
    
    def save_to_csv(self, data: List[Dict], filename: str = "github_repo_data.csv"):
        """
        Save data to CSV file, appending to historical record.
        Each row represents one repository for one date.
        """
        if not data:
            print("No data to save")
            return
        
        # Load existing CSV if it exists
        existing_rows = []
        file_exists = os.path.exists(filename)
        
        if file_exists:
            try:
                with open(filename, "r", encoding="utf-8", newline="") as f:
                    reader = csv.DictReader(f)
                    existing_rows = list(reader)
            except Exception as e:
                print(f"Warning: Could not read existing CSV: {e}")
        
        # Extract date from data
        target_date = data[0].get("date", "") if data else ""
        
        # Remove existing rows for this date if they exist
        if target_date:
            existing_rows = [row for row in existing_rows if row.get("date") != target_date]
        
        # Create new rows
        new_rows = []
        for repo_data in data:
            repo = repo_data["repository"]
            traffic = repo_data["traffic"]
            commits = repo_data["commits"]
            
            row = {
                "date": repo_data.get("date", ""),
                "repository": repo["full_name"],
                "private": repo["private"],
                "language": repo.get("language", ""),
                "stars": repo["stargazers_count"],
                "forks": repo["forks_count"],
                "watchers": repo["watchers_count"],
                "open_issues": repo["open_issues_count"],
                "views": traffic.get("views", 0),
                "views_uniques": traffic.get("views_uniques", 0),
                "clones": traffic.get("clones", 0),
                "clones_uniques": traffic.get("clones_uniques", 0),
                "commits": commits.get("commits", 0),
                "additions": commits.get("additions", 0),
                "deletions": commits.get("deletions", 0),
                "net_change": commits.get("net_change", 0),
                "scraped_at": repo_data.get("scraped_at", "")
            }
            new_rows.append(row)
        
        # Combine and save
        all_rows = existing_rows + new_rows
        
        if all_rows:
            fieldnames = [
                "date", "repository", "private", "language", "stars", "forks",
                "watchers", "open_issues", "views", "views_uniques", "clones",
                "clones_uniques", "commits", "additions", "deletions", "net_change",
                "scraped_at"
            ]
            
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_rows)
            print(f"Data saved to {filename} (historical record)")


def main():
    """Main function to run the scraper."""
    # Get token from environment variable or config
    token = os.getenv("GITHUB_TOKEN")
    
    if not token:
        # Try to read from config file
        config_file = "config.json"
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                config = json.load(f)
                token = config.get("github_token")
    
    if not token:
        print("Error: GitHub token not found!")
        print("Please set GITHUB_TOKEN environment variable or create config.json")
        print("See README.md for instructions on creating a Personal Access Token")
        return
    
    # Get username (default to Sesquii)
    username = os.getenv("GITHUB_USERNAME", "Sesquii")
    
    # Create scraper instance
    scraper = GitHubScraper(token=token, username=username)
    
    # Scrape all repositories for data from 7 days ago
    print(f"Scraping repositories for {username}...")
    print("Collecting data from exactly 7 days ago (single day snapshot)")
    data = scraper.scrape_all_repos(days_ago=7)
    
    if data:
        # Save to both JSON and CSV
        scraper.save_to_json(data)
        scraper.save_to_csv(data)
        print(f"\nSuccessfully scraped {len(data)} repositories!")
    else:
        print("No data collected")


if __name__ == "__main__":
    main()

