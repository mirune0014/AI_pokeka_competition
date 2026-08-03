from __future__ import annotations

import io
import unittest
from unittest.mock import patch
import urllib.error

from infrastructure.tools.download_episode_samples import (
    collect_dataset_files,
    choose_files,
    choose_score_ranked_files,
    list_dataset_files_kaggle,
    read_json,
)


class DatasetFilePaginationTest(unittest.TestCase):
    def test_collects_pages_until_token_is_absent(self):
        calls = []

        def loader(owner, slug, token):
            calls.append((owner, slug, token))
            if token == "":
                return {"datasetFiles": [{"name": "a"}], "nextPageToken": "next"}
            return {"datasetFiles": [{"name": "b"}], "nextPageToken": ""}

        result = collect_dataset_files("owner", "slug", max_pages=5, page_loader=loader)
        self.assertEqual([item["name"] for item in result], ["a", "b"])
        self.assertEqual(calls, [("owner", "slug", ""), ("owner", "slug", "next")])

    def test_repeated_token_is_rejected(self):
        def loader(_owner, _slug, _token):
            return {"datasetFiles": [], "nextPageToken": "same"}

        with self.assertRaisesRegex(RuntimeError, "repeated"):
            collect_dataset_files("owner", "slug", max_pages=3, page_loader=loader)

    def test_json_fetch_retries_transient_http_error(self):
        with patch(
            "infrastructure.tools.download_episode_samples.urllib.request.urlopen",
            side_effect=[urllib.error.HTTPError("url", 404, "temporary", {}, None), io.BytesIO(b'{"ok":true}')],
        ):
            self.assertEqual(read_json("https://example.invalid", attempts=2, backoff_seconds=0), {"ok": True})

    def test_authenticated_listing_normalizes_sdk_response(self):
        file_value = type("File", (), {"name": "episode.json", "total_bytes": 123})()
        response = type("Response", (), {"files": [file_value], "next_page_token": "next"})()
        client = unittest.mock.Mock()
        client.dataset_list_files.return_value = response
        result = list_dataset_files_kaggle(
            "owner", "slug", "token", page_size=200, api_client=client
        )
        self.assertEqual(result, {
            "datasetFiles": [{"name": "episode.json", "totalBytes": 123}],
            "nextPageToken": "next",
        })
        client.dataset_list_files.assert_called_once_with(
            "owner/slug", page_token="token", page_size=200
        )


class DatasetFileSelectionTest(unittest.TestCase):
    def test_even_selection_covers_first_and_last(self):
        files = [{"name": str(index)} for index in range(10)]
        selected = choose_files(files, 4, "even")
        self.assertEqual([item["name"] for item in selected], ["0", "3", "6", "9"])

    def test_single_even_selection_uses_middle(self):
        files = [{"name": str(index)} for index in range(5)]
        self.assertEqual(choose_files(files, 1, "even"), [{"name": "2"}])

    def test_score_ranked_selection_uses_manifest_metric(self):
        files = [
            {"name": "1.json", "totalBytes": 1},
            {"name": "2.json", "totalBytes": 2},
            {"name": "manifest.csv", "totalBytes": 3},
        ]
        manifest = [
            {"episode_id": "1", "avg_score": "1200", "min_score": "900"},
            {"episode_id": "2", "avg_score": "1100", "min_score": "1000"},
        ]
        selected = choose_score_ranked_files(files, manifest, 1, "min_score")
        self.assertEqual(selected, [{"name": "2.json", "totalBytes": 2}])

    def test_score_ranked_selection_ignores_missing_and_invalid_rows(self):
        files = [{"name": "1.json"}, {"name": "2.json"}]
        manifest = [
            {"episode_id": "missing", "avg_score": "9999"},
            {"episode_id": "1", "avg_score": "invalid"},
            {"episode_id": "2", "avg_score": "1200"},
        ]
        self.assertEqual(
            choose_score_ranked_files(files, manifest, 3, "avg_score"),
            [{"name": "2.json"}],
        )


if __name__ == "__main__":
    unittest.main()
