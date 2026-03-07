#!/usr/bin/env python3
"""Tests for LinkedIn Profile Scraper.

Unit tests for pure functions + E2E test against live Bright Data API.

Usage:
    python test_scraper.py              # run all tests
    python test_scraper.py TestUnit     # unit tests only
    python test_scraper.py TestE2E      # E2E test only (requires API key)
"""

import csv
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import linkedin_profile_scraper as scraper


class TestUnit(unittest.TestCase):
    """Unit tests for pure utility functions (no API calls)."""

    # -- extract_emails --------------------------------------------------

    def test_extract_emails_basic(self):
        emails = scraper.extract_emails("contact me at hello@example.org")
        self.assertIn("hello@example.org", emails)

    def test_extract_emails_multiple(self):
        text = "reach out to a@b.com or c@d.co.uk for info"
        emails = scraper.extract_emails(text)
        self.assertGreaterEqual(len(emails), 2)

    def test_extract_emails_empty(self):
        self.assertEqual(scraper.extract_emails(""), [])
        self.assertEqual(scraper.extract_emails(None), [])

    def test_extract_emails_blacklist(self):
        text = "icon@image.png noreply@svc.com real@company.com"
        emails = scraper.extract_emails(text)
        self.assertIn("real@company.com", emails)
        self.assertNotIn("noreply@svc.com", emails)

    # -- normalize_linkedin_url ------------------------------------------

    def test_normalize_linkedin_url_standard(self):
        result = scraper.normalize_linkedin_url("https://www.linkedin.com/in/johndoe")
        self.assertEqual(result, "https://www.linkedin.com/in/johndoe/")

    def test_normalize_linkedin_url_with_trailing_slash(self):
        result = scraper.normalize_linkedin_url("https://www.linkedin.com/in/johndoe/")
        self.assertEqual(result, "https://www.linkedin.com/in/johndoe/")

    def test_normalize_linkedin_url_bare_slug(self):
        result = scraper.normalize_linkedin_url("johndoe")
        self.assertIn("linkedin.com/in/johndoe", result)

    def test_normalize_linkedin_url_empty(self):
        self.assertEqual(scraper.normalize_linkedin_url(""), "")
        self.assertEqual(scraper.normalize_linkedin_url(None), "")

    # -- format_skills ---------------------------------------------------

    def test_format_skills_list_of_strings(self):
        result = scraper.format_skills(
            ["Python", "JavaScript", "SQL", "React", "AWS", "Docker"]
        )
        self.assertIn("Python", result)
        self.assertIn("AWS", result)
        # Should only include top 5
        self.assertNotIn("Docker", result)

    def test_format_skills_list_of_dicts(self):
        skills = [{"name": "Python"}, {"name": "SQL"}, {"skill": "React"}]
        result = scraper.format_skills(skills)
        self.assertIn("Python", result)
        self.assertIn("SQL", result)

    def test_format_skills_empty(self):
        self.assertEqual(scraper.format_skills([]), "")
        self.assertEqual(scraper.format_skills(None), "")

    def test_format_skills_string(self):
        result = scraper.format_skills("Python, SQL, React")
        self.assertIn("Python", result)

    # -- extract_current_company -----------------------------------------

    def test_extract_current_company_direct(self):
        data = {"current_company": "Acme Inc"}
        self.assertEqual(scraper.extract_current_company(data), "Acme Inc")

    def test_extract_current_company_from_experience(self):
        data = {"experience": [{"company": "TechCo"}, {"company": "OldCo"}]}
        self.assertEqual(scraper.extract_current_company(data), "TechCo")

    def test_extract_current_company_empty(self):
        self.assertEqual(scraper.extract_current_company({}), "")

    # -- read_profiles_csv -----------------------------------------------

    def test_read_profiles_csv_url_mode(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        ) as f:
            f.write("url\n")
            f.write("https://www.linkedin.com/in/johndoe/\n")
            f.write("https://www.linkedin.com/in/janedoe/\n")
            path = f.name
        try:
            mode, data = scraper.read_profiles_csv(path)
            self.assertEqual(mode, "url")
            self.assertEqual(len(data), 2)
            self.assertIn("johndoe", data[0])
        finally:
            os.unlink(path)

    def test_read_profiles_csv_name_mode(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        ) as f:
            f.write("first_name,last_name,company\n")
            f.write("John,Doe,Acme\n")
            f.write("Jane,Smith,TechCo\n")
            path = f.name
        try:
            mode, data = scraper.read_profiles_csv(path)
            self.assertEqual(mode, "name")
            self.assertEqual(len(data), 2)
            self.assertEqual(data[0], ("John", "Doe", "Acme"))
        finally:
            os.unlink(path)


class TestE2E(unittest.TestCase):
    """End-to-end test against live Bright Data API.

    Requires BRIGHT_DATA_API_KEY environment variable.
    Uses 1 profile URL to keep costs low.
    """

    def setUp(self):
        if not os.environ.get("BRIGHT_DATA_API_KEY"):
            self.skipTest("BRIGHT_DATA_API_KEY not set")
        self.output_csv = tempfile.mktemp(suffix=".csv")
        self.input_csv = tempfile.mktemp(suffix=".csv")
        with open(self.input_csv, "w", newline="") as f:
            f.write("url\n")
            f.write("https://www.linkedin.com/in/satyanadella/\n")

    def tearDown(self):
        for path in (self.output_csv, self.input_csv):
            if os.path.exists(path):
                os.unlink(path)

    def test_full_pipeline(self):
        """Run the full scraper pipeline with minimal input."""
        original_argv = sys.argv
        sys.argv = ["linkedin_profile_scraper.py", self.input_csv, self.output_csv]
        try:
            scraper.main()
        finally:
            sys.argv = original_argv

        self.assertTrue(
            os.path.exists(self.output_csv),
            f"Output CSV was not created at {self.output_csv}",
        )

        with open(self.output_csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        expected_cols = {
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
        }
        if rows:
            actual_cols = set(rows[0].keys())
            self.assertEqual(
                actual_cols,
                expected_cols,
                f"CSV columns mismatch.\nExpected: {expected_cols}\nGot: {actual_cols}",
            )

        self.assertGreater(
            len(rows),
            0,
            "No profiles found. The API may have returned no results.",
        )

        # Verify Satya Nadella's profile data
        row = rows[0]
        if row["name"]:
            # Name should contain "Nadella" or "Satya"
            name_lower = row["name"].lower()
            self.assertTrue(
                "nadella" in name_lower or "satya" in name_lower,
                f"Expected Nadella profile, got: {row['name']}",
            )
        if row["profile_url"]:
            self.assertIn("linkedin.com", row["profile_url"])

        print(f"\n  E2E Result: {len(rows)} profiles enriched")
        print(f"  Name: {row['name']}")
        print(f"  Headline: {row['headline'][:80] if row['headline'] else 'N/A'}")
        print(f"  Company: {row['company'] or 'N/A'}")
        print(f"  Email: {row['email'] or 'none'}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
