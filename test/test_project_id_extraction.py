import re
import unittest


def extract_project_id(input_str: str) -> str | None:
    """Extract a project GUID from a raw string or a Riverscapes URL.

    Replicated locally to avoid importing util.py, which has a hard
    QGIS dependency (qgis.core) at module level.

    Source: src/classes/util.py:234
    """
    if not input_str:
        return None

    input_str = input_str.strip()

    uuid_pattern = r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"

    # Check if the input is just a UUID
    if re.fullmatch(uuid_pattern, input_str):
        return input_str

    # Valid: /p/<guid>, /rv/<guid>
    url_pattern = r"(?:https?://[^/]+)?/(?:p|rv)/(" + uuid_pattern + r")(?:[/?]|$)"

    match = re.search(url_pattern, input_str)
    if match:
        return match.group(1)

    return None


class TestProjectIdExtraction(unittest.TestCase):
    def test_valid_guids(self):
        # Plain GUID
        guid = "6a3210a1-8f4a-4536-a4ac-c4fe5002f83e"
        self.assertEqual(extract_project_id(guid), guid)

    def test_valid_urls(self):
        guid = "6a3210a1-8f4a-4536-a4ac-c4fe5002f83e"

        valid_urls = [f"https://data.riverscapes.net/p/{guid}/", f"https://data.riverscapes.net/p/{guid}/datasets", f"https://data.riverscapes.net/rv/{guid}?do=1&lo=1&vm=Default&bl=SAT"]

        for url in valid_urls:
            self.assertEqual(extract_project_id(url), guid, f"Failed to extract from {url}")

    def test_invalid_urls(self):
        # These look like projects but are distinct types (collection, dataset, org, user)
        invalid_urls = [
            "https://data.riverscapes.net/c/8a9d4f6f-deb1-4076-a399-d557387f7183/",
            "https://data.riverscapes.net/d/4cd7e2e4-8d6c-4083-a17a-5cd5d7c60190/",
            "https://data.riverscapes.net/o/5d5bcccc-6632-4054-85f1-19501a6b3cdf/",
            "https://data.riverscapes.net/u/b4f012d5-a923-4007-8673-57f2f5dd5b04/",
        ]

        for url in invalid_urls:
            self.assertIsNone(extract_project_id(url), f"Should not have extracted ID from {url}")

    def test_extra_edge_cases(self):
        # Test just path without domain
        guid = "6a3210a1-8f4a-4536-a4ac-c4fe5002f83e"
        self.assertEqual(extract_project_id(f"/p/{guid}/"), guid)
        self.assertEqual(extract_project_id(f"/rv/{guid}"), guid)

        # Test random text that shouldn't match
        self.assertIsNone(extract_project_id("not a url or guid"))


if __name__ == "__main__":
    unittest.main()
