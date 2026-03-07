#!/usr/bin/env python3
"""LinkedIn Profile Enrichment Tool via Bright Data.

Workflow: Profile URLs CSV -> BD LinkedIn Profiles Dataset -> Extract contact info -> Output CSV

Usage:
    python linkedin_profile_scraper.py profiles.csv output_leads.csv

Requires:
    - Python 3.9+
    - Bright Data API key (set BRIGHT_DATA_API_KEY environment variable)
    - Active Bright Data subscription with LinkedIn datasets enabled
"""

import csv
import json
import os
import re
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# ============================================================
# CONFIGURATION - Set your API key as an environment variable
# ============================================================
API_KEY = os.environ.get("BRIGHT_DATA_API_KEY", "")
if not API_KEY:
    print("ERROR: Set your Bright Data API key:")
    print("  Windows:  set BRIGHT_DATA_API_KEY=your-api-key-here")
    print("  Mac/Linux: export BRIGHT_DATA_API_KEY=your-api-key-here")
    print()
    print("Get your API key from: https://brightdata.com/cp/setting/users")
    sys.exit(1)

# Bright Data dataset ID
PROFILES_DATASET_ID = "gd_l1viktl72bvl7bjuj0"  # LinkedIn - Profiles

BASE_URL = "https://api.brightdata.com/datasets/v3"

POLL_INTERVAL = 15  # seconds between status checks
POLL_TIMEOUT = 1800  # 30 minutes max wait

# Regex pattern to find email addresses in text
EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

# False-positive email patterns to filter out
EMAIL_BLACKLIST_PATTERNS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    "noreply@",
    "no-reply@",
    "example.com",
    "email.com",
    "yourname@",
    "username@",
    "test@",
}

# Default profiles used when no CSV is provided
DEFAULT_PROFILES = [
    "https://www.linkedin.com/in/jeffweiner08/",
    "https://www.linkedin.com/in/satyanadella/",
    "https://www.linkedin.com/in/rbranson/",
]


def api_request(method, url, data=None):
    """Make an HTTP request to the Bright Data API."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    body = json.dumps(data).encode() if data else None
    req = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=180) as resp:
            raw = resp.read().decode()
            if not raw.strip():
                return None
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return raw.strip()
    except HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        print(f"  HTTP {e.code}: {body_text[:500]}")
        raise
    except URLError as e:
        print(f"  Network error: {e.reason}")
        raise


def read_profiles_csv(path):
    """Read LinkedIn profile URLs or name-based lookups from a CSV file.

    Supports two formats:

    Format 1 (URLs):
        url
        https://www.linkedin.com/in/jeffweiner08/
        https://www.linkedin.com/in/satyanadella/

    Format 2 (Names for discovery):
        first_name,last_name,company
        Jeff,Weiner,LinkedIn
        Satya,Nadella,Microsoft

    Returns (mode, data) where:
        mode = "url" and data = list of URLs
        mode = "name" and data = list of (first_name, last_name, company) tuples
    """
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            return "url", []

        # Detect format from header
        header_lower = [h.lower().strip() for h in header]

        if "first_name" in header_lower or "firstname" in header_lower:
            # Name-based format
            first_idx = next(
                (
                    i
                    for i, h in enumerate(header_lower)
                    if h in ("first_name", "firstname")
                ),
                0,
            )
            last_idx = next(
                (
                    i
                    for i, h in enumerate(header_lower)
                    if h in ("last_name", "lastname")
                ),
                1,
            )
            company_idx = next(
                (
                    i
                    for i, h in enumerate(header_lower)
                    if h in ("company", "organization", "org")
                ),
                2,
            )

            names = []
            for row in reader:
                if not row or not row[0].strip():
                    continue
                first = row[first_idx].strip() if len(row) > first_idx else ""
                last = row[last_idx].strip() if len(row) > last_idx else ""
                company = row[company_idx].strip() if len(row) > company_idx else ""
                if first or last:
                    names.append((first, last, company))
            return "name", names

        # URL-based format
        url_words = {"url", "urls", "profile", "profiles", "linkedin", "link"}
        urls = []

        # Check if header is actually a URL (no header row)
        if header[0].lower().strip() not in url_words:
            val = header[0].strip()
            if val and "linkedin.com" in val:
                urls.append(val)

        for row in reader:
            if not row or not row[0].strip():
                continue
            urls.append(row[0].strip())
        return "url", urls


def normalize_linkedin_url(url):
    """Normalize a LinkedIn profile URL."""
    if not url:
        return ""
    url = str(url).strip()
    if not url.startswith("http"):
        url = f"https://www.linkedin.com/in/{url}/"
    url = url.rstrip("/") + "/"
    return url


def trigger_collection(dataset_id, inputs, discover_by=None):
    """Trigger a Bright Data dataset collection. Returns snapshot_id."""
    url = f"{BASE_URL}/trigger?dataset_id={dataset_id}&notify=false&include_errors=true"
    if discover_by:
        url += f"&type=discover_new&discover_by={discover_by}"
    payload = {"input": inputs}
    print(f"  Triggering collection with {len(inputs)} input(s)...")
    resp = api_request("POST", url, payload)
    if isinstance(resp, dict) and "snapshot_id" in resp:
        return resp["snapshot_id"]
    if isinstance(resp, str):
        return resp
    raise RuntimeError(f"Unexpected trigger response: {resp}")


def poll_until_ready(snapshot_id):
    """Poll Bright Data until the snapshot data is ready for download."""
    url = f"{BASE_URL}/progress/{snapshot_id}"
    start = time.time()
    last_status = None
    while time.time() - start < POLL_TIMEOUT:
        try:
            resp = api_request("GET", url)
        except HTTPError:
            time.sleep(POLL_INTERVAL)
            continue

        status = resp.get("status") if isinstance(resp, dict) else str(resp)
        if status != last_status:
            elapsed = int(time.time() - start)
            print(f"  Status: {status} ({elapsed}s elapsed)")
            last_status = status

        if status == "ready":
            time.sleep(5)
            return
        if status in ("failed", "error", "cancelled"):
            raise RuntimeError(
                f"Collection failed with status: {status}. Details: {resp}"
            )

        time.sleep(POLL_INTERVAL)

    raise TimeoutError(f"Collection timed out after {POLL_TIMEOUT}s")


def download_snapshot(snapshot_id, retries=3):
    """Download snapshot results as JSON. Retries if data isn't ready yet."""
    url = f"{BASE_URL}/snapshot/{snapshot_id}?format=json"
    for attempt in range(retries):
        print(
            f"  Downloading snapshot {snapshot_id} (attempt {attempt + 1}/{retries})..."
        )
        try:
            result = api_request("GET", url)
        except Exception as e:
            print(f"  Download error: {e}")
            if attempt < retries - 1:
                time.sleep(10)
                continue
            raise

        if isinstance(result, dict) and "snapshot_id" in result:
            print(f"  Data not ready yet, retrying...")
            if attempt < retries - 1:
                time.sleep(15)
                continue
            raise RuntimeError(f"Snapshot data not available after {retries} attempts")

        if isinstance(result, list):
            return result

        print(f"  Unexpected response type: {type(result).__name__}, retrying...")
        if attempt < retries - 1:
            time.sleep(10)
            continue
        return result

    return None


def extract_emails(text):
    """Extract email addresses from text, filtering false positives."""
    if not text:
        return []
    raw = set(EMAIL_REGEX.findall(str(text)))
    filtered = []
    for email in raw:
        lower = email.lower()
        if any(pat in lower for pat in EMAIL_BLACKLIST_PATTERNS):
            continue
        filtered.append(email)
    return filtered


def format_skills(skills_data):
    """Format skills list into a semicolon-separated string (top 5)."""
    if not skills_data:
        return ""
    if isinstance(skills_data, str):
        return skills_data[:200]
    if isinstance(skills_data, list):
        skill_names = []
        for s in skills_data[:5]:
            if isinstance(s, dict):
                name = s.get("name", "") or s.get("skill", "") or str(s)
                skill_names.append(str(name))
            else:
                skill_names.append(str(s))
        return "; ".join(skill_names)
    return str(skills_data)[:200]


def extract_current_company(profile_data):
    """Extract current company from experience data."""
    # Direct field
    company = (
        profile_data.get("current_company", "")
        or profile_data.get("company", "")
        or profile_data.get("current_company_name", "")
        or ""
    )
    if company:
        return str(company)

    # Try from experience array
    experience = profile_data.get("experience", [])
    if isinstance(experience, list) and experience:
        latest = experience[0]
        if isinstance(latest, dict):
            return latest.get("company", "") or latest.get("company_name", "") or ""

    return ""


def main():
    input_csv = sys.argv[1] if len(sys.argv) > 1 else None
    output_csv = sys.argv[2] if len(sys.argv) > 2 else "output_leads.csv"

    # == Step 1: Get profiles =============================================
    if input_csv and os.path.exists(input_csv):
        print(f"[1/5] Reading profiles from {input_csv}")
        mode, data = read_profiles_csv(input_csv)
    else:
        print("[1/5] Using default profiles (no CSV provided)")
        mode = "url"
        data = DEFAULT_PROFILES

    if mode == "url":
        print(f"  Mode: URL-based enrichment")
        print(f"  Profiles to enrich: {len(data)}")
        for p in data[:10]:
            print(f"    {p}")
        if len(data) > 10:
            print(f"    ... and {len(data) - 10} more")
    else:
        print(f"  Mode: Name-based discovery")
        print(f"  Names to look up: {len(data)}")
        for first, last, company in data[:10]:
            print(f"    {first} {last}" + (f" ({company})" if company else ""))
        if len(data) > 10:
            print(f"    ... and {len(data) - 10} more")

    # == Step 2: Trigger collection =======================================
    print(f"\n[2/5] Triggering Bright Data LinkedIn Profiles collection...")

    if mode == "url":
        inputs = [{"url": normalize_linkedin_url(url)} for url in data]
        snapshot_id = trigger_collection(PROFILES_DATASET_ID, inputs)
    else:
        inputs = []
        for first, last, company in data:
            entry = {"first_name": first, "last_name": last}
            if company:
                entry["company"] = company
            inputs.append(entry)
        snapshot_id = trigger_collection(
            PROFILES_DATASET_ID, inputs, discover_by="name"
        )

    print(f"  Snapshot ID: {snapshot_id}")

    # == Step 3: Wait + download ==========================================
    print(f"\n[3/5] Waiting for collection to complete (this may take 2-5 minutes)...")
    poll_until_ready(snapshot_id)

    print("  Downloading results...")
    results = download_snapshot(snapshot_id)
    if not results:
        print("  No profile data returned. Exiting.")
        return

    results = [r for r in results if isinstance(r, dict)]
    errors = [r for r in results if r.get("error")]
    print(
        f"  Got {len(results)} results ({len(results) - len(errors)} profiles, {len(errors)} errors)"
    )

    for err in errors:
        err_input = err.get("input", {})
        err_id = ""
        if isinstance(err_input, dict):
            err_id = (
                err_input.get("url", "")
                or f"{err_input.get('first_name', '')} {err_input.get('last_name', '')}"
            )
        print(f"    Error: {err_id} -> {err.get('error', 'unknown')}")

    # == Step 4: Extract contact info =====================================
    print(
        f"\n[4/5] Extracting contact info from {len(results) - len(errors)} profiles..."
    )
    rows = []
    email_count = 0

    for pr in results:
        if pr.get("error"):
            continue

        # Profile fields
        profile_url = (
            pr.get("profile_url", "")
            or pr.get("url", "")
            or pr.get("linkedin_url", "")
            or ""
        )
        name = pr.get("name", "") or pr.get("full_name", "") or ""
        headline = pr.get("headline", "") or pr.get("title", "") or ""
        company = extract_current_company(pr)
        location = (
            pr.get("location", "") or pr.get("city", "") or pr.get("region", "") or ""
        )
        connections = (
            pr.get("connections", "")
            or pr.get("num_connections", "")
            or pr.get("connection_count", "")
        )

        # About/summary
        about = (
            pr.get("about", "")
            or pr.get("summary", "")
            or pr.get("description", "")
            or ""
        )

        # Website
        websites = (
            pr.get("websites", "") or pr.get("links", "") or pr.get("website", "") or ""
        )
        if isinstance(websites, list):
            website_str = "; ".join(
                str(w.get("url", w) if isinstance(w, dict) else w)
                for w in websites[:3]
                if w
            )
        else:
            website_str = str(websites).strip() if websites else ""

        # Skills
        skills = format_skills(pr.get("skills", []))

        # Email extraction
        direct_email = pr.get("email", "") or pr.get("email_address", "") or ""
        about_emails = extract_emails(about)

        all_emails = list(about_emails)
        if direct_email and direct_email not in all_emails:
            all_emails.append(direct_email)

        email_str = "; ".join(all_emails) if all_emails else ""
        if all_emails:
            email_count += len(all_emails)

        rows.append(
            {
                "profile_url": profile_url,
                "name": name,
                "headline": headline,
                "company": company,
                "location": str(location),
                "connections": connections,
                "email": email_str,
                "website": website_str[:200],
                "about_preview": str(about)[:300].replace("\n", " "),
                "skills": skills,
            }
        )

    print(f"  Enriched {len(rows)} profiles")
    print(f"  Emails found: {email_count}")

    # == Step 5: Write output CSV =========================================
    print(f"\n[5/5] Writing output to {output_csv}...")
    fieldnames = [
        "profile_url",
        "name",
        "headline",
        "company",
        "location",
        "connections",
        "email",
        "website",
        "about_preview",
        "skills",
    ]
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone! {len(rows)} profiles written to {output_csv}")
    print(f"  Profiles with emails: {sum(1 for r in rows if r['email'])}")
    print(f"  Total unique emails: {email_count}")


if __name__ == "__main__":
    main()
