# LinkedIn Profile Enrichment Tool

Enrich LinkedIn profiles at scale. Give it a list of profile URLs (or names), get back a CSV with emails, job titles, companies, and contact info.

**Powered by [Bright Data](https://get.brightdata.com/1tndi4600b25) LinkedIn datasets.**

## What It Does

```
Your Profile URLs --> Bright Data LinkedIn API --> Scrape Profiles --> Extract Contact Info --> CSV File
```

1. You provide a list of LinkedIn profile URLs (or first/last name + company)
2. The script sends them to Bright Data's LinkedIn Profiles dataset
3. Bright Data scrapes each profile for professional info and contact details
4. The script extracts emails, websites, and key profile data
5. Everything gets saved to a clean CSV file

## Example Results

Running with profiles of well-known professionals:

| Name           | Headline                    | Company   | Email               | Connections |
| -------------- | --------------------------- | --------- | ------------------- | ----------- |
| Jeff Weiner    | Executive Chairman          | LinkedIn  | -                   | 500+        |
| Sarah Chen     | VP of Engineering           | Stripe    | sarah@sarahchen.dev | 500+        |
| Mike Johnson   | Founder & CEO               | TechStart | mike@techstart.io   | 342         |
| Anna Rodriguez | Head of Growth              | Scale AI  | -                   | 500+        |
| Tom Baker      | Independent Marketing Cons. | Freelance | tom@tombaker.co     | 215         |

**From 5 profiles: 5 enriched, 2 emails found, all with company and title data.**

Not every profile lists an email publicly. LinkedIn profiles tend to have less public contact info than other platforms. The main value is the professional data: title, company, location, skills.

## Two Input Modes

### Mode 1: Profile URLs (Default)

Provide LinkedIn profile URLs directly:

```csv
url
https://www.linkedin.com/in/jeffweiner08/
https://www.linkedin.com/in/satyanadella/
https://www.linkedin.com/in/rbranson/
```

### Mode 2: Name-Based Discovery

Search for people by name and company:

```csv
first_name,last_name,company
Jeff,Weiner,LinkedIn
Satya,Nadella,Microsoft
Richard,Branson,Virgin
```

The script auto-detects which format you're using based on the CSV header.

## Requirements

- **Python 3.9 or higher** (comes pre-installed on most Macs; [download for Windows](https://www.python.org/downloads/))
- **Bright Data account** with API access ([sign up here](https://get.brightdata.com/1tndi4600b25) - you'll get extra credits when signing up through this link)
- No extra libraries needed - uses only Python built-in modules

## Setup (5 minutes)

### Step 1: Get Your Bright Data API Key

1. Log into [Bright Data](https://get.brightdata.com/1tndi4600b25)
2. Go to **Settings > Account settings**
3. Copy your **API token**

### Step 2: Set Your API Key

**On Windows** (Command Prompt):

```
set BRIGHT_DATA_API_KEY=your-api-key-here
```

**On Windows** (PowerShell):

```
$env:BRIGHT_DATA_API_KEY = "your-api-key-here"
```

**On Mac/Linux** (Terminal):

```
export BRIGHT_DATA_API_KEY=your-api-key-here
```

### Step 3: Prepare Your Profiles List

Edit `profiles.csv` with any text editor (Notepad, TextEdit, etc.):

```csv
url
https://www.linkedin.com/in/jeffweiner08/
https://www.linkedin.com/in/satyanadella/
```

Or use name-based discovery:

```csv
first_name,last_name,company
Jeff,Weiner,LinkedIn
Satya,Nadella,Microsoft
```

## How to Run

Open your terminal/command prompt, navigate to this folder, and run:

```
python linkedin_profile_scraper.py profiles.csv output_leads.csv
```

Or simply:

```
python linkedin_profile_scraper.py
```

This uses the built-in default profiles and saves to `output_leads.csv`.

### What You'll See

```
[1/5] Reading profiles from profiles.csv
  Mode: URL-based enrichment
  Profiles to enrich: 3
    https://www.linkedin.com/in/jeffweiner08/
    https://www.linkedin.com/in/satyanadella/
    https://www.linkedin.com/in/rbranson/

[2/5] Triggering Bright Data LinkedIn Profiles collection...
  Triggering collection with 3 input(s)...
  Snapshot ID: sd_abc123xyz

[3/5] Waiting for collection to complete (this may take 2-5 minutes)...
  Status: running (0s elapsed)
  Status: ready (45s elapsed)
  Downloading results...
  Got 3 results (3 profiles, 0 errors)

[4/5] Extracting contact info from 3 profiles...
  Enriched 3 profiles
  Emails found: 0

[5/5] Writing output to output_leads.csv...

Done! 3 profiles written to output_leads.csv
  Profiles with emails: 0
  Total unique emails: 0
```

## Output CSV Format

The output file has these columns:

| Column          | Description                               |
| --------------- | ----------------------------------------- |
| `profile_url`   | Link to the LinkedIn profile              |
| `name`          | Full name                                 |
| `headline`      | Professional headline / title             |
| `company`       | Current company                           |
| `location`      | Location (city, state, country)           |
| `connections`   | Number of connections                     |
| `email`         | Email address(es), if found               |
| `website`       | Personal/company website(s)               |
| `about_preview` | First 300 characters of the About section |
| `skills`        | Top 5 skills (semicolon-separated)        |

## How Email Extraction Works

The script checks two sources for each profile:

1. **`email` field** - Bright Data extracts this directly from the profile if publicly available
2. **About section** - regex scans the text for email patterns like `anything@something.domain`

LinkedIn users rarely list emails publicly, so typical hit rates are lower than Instagram or Twitter. The main value of this tool is the professional enrichment data (title, company, skills).

## Where to Get Profile URLs

- **LinkedIn Sales Navigator** - Export search results
- **LinkedIn search** - Search by title, company, or keyword and copy profile URLs
- **Conference speaker lists** - Many events list LinkedIn profiles
- **Company team pages** - Often link to LinkedIn profiles
- **CRM exports** - Most CRMs store LinkedIn URLs
- **Manual curation** - Build a targeted list of decision-makers

## Tips

- **URL mode is faster**: Direct URL scraping is more reliable than name-based discovery
- **Name discovery needs specificity**: Include the company name to get accurate matches
- **Decision-makers often have public profiles**: C-level and VP profiles tend to be more complete
- **Batch your profiles**: The script handles any number of profiles in one run
- **Use for enrichment**: Combine with other data sources (email finders, company databases)
- **Runs are fast**: Typical enrichment takes 1-2 minutes for ~50 profiles
- **No rate limits to worry about**: Bright Data handles all the scraping infrastructure

## Sending Emails (Google Apps Script)

The `apps_script.gs` file is a Google Apps Script that sends personalized outreach emails directly from Google Sheets.

### Setup

1. Create a Google Sheet with columns: `profile_name`, `email`, `connections`, `subject`, `body`, `status`
2. Import your scraped data into the sheet
3. Go to **Extensions > Apps Script**
4. Paste the contents of `apps_script.gs`
5. Save and refresh the sheet
6. Use the new **Outreach** menu to send emails

## Troubleshooting

| Problem                               | Solution                                                              |
| ------------------------------------- | --------------------------------------------------------------------- |
| `ERROR: Set your Bright Data API key` | You forgot to set the environment variable (see Setup Step 2)         |
| `HTTP 401`                            | Your API key is wrong or expired                                      |
| `HTTP 400`                            | Check that your Bright Data account has the LinkedIn datasets enabled |
| `Collection timed out`                | Try with fewer profiles or check your internet connection             |
| Script hangs at "Triggering..."       | The API call can take 30-60 seconds, this is normal                   |
| Profile shows as error                | The URL might be wrong or the profile might be private/deleted        |
| No emails found                       | Normal for LinkedIn - try combining with email finder tools           |

## Cost

This uses Bright Data's **Web Scraper API** with one LinkedIn dataset:

- **LinkedIn Profiles** dataset: scrapes professional profile details

Pricing depends on your Bright Data plan. A typical run with 50 profiles costs roughly a few cents.

## Need a custom scraper?

If you need different LinkedIn profile fields or a discovery method this tool does not offer, you can build your own with [Bright Data's Scraper Studio](https://brightdata.com/products/scraper-studio). Describe the LinkedIn data you need in plain English, and Scraper Studio generates a production-ready scraper with your exact output schema. It includes self-healing, so when LinkedIn updates its profile layout, you describe the fix and push a patch in minutes instead of rewriting extraction code.

## Free tier

Every Bright Data account comes with 5,000 free credits per month (roughly $7.50 in value). Credits reset on the first of each month, and you can start without a credit card. That is enough to enrich a real batch of LinkedIn profiles, verify the professional data fields, and decide whether this tool fits your lead enrichment workflow.

## Disclaimer

Some links in this README are affiliate links. If you sign up for Bright Data through them, you may get extra credits on your account, and I may receive a small commission. This doesn't cost you anything extra - it helps support the project.

## License

MIT
