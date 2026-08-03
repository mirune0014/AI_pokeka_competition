from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.parse
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable


INDEX_REF = "kaggle/pokemon-tcg-ai-battle-episodes-index"
DATASET_API = "https://www.kaggle.com/api/v1/datasets"


def read_json(url: str, *, attempts: int = 5, backoff_seconds: float = 0.5) -> dict:
    if attempts <= 0 or backoff_seconds < 0:
        raise ValueError("invalid retry configuration")
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(url) as response:
                return json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError):
            if attempt + 1 == attempts:
                raise
            time.sleep(backoff_seconds * (2 ** attempt))
    raise AssertionError("retry loop did not terminate")


def download(
    url: str,
    output: Path,
    *,
    attempts: int = 5,
    backoff_seconds: float = 0.5,
) -> None:
    if attempts <= 0 or backoff_seconds < 0:
        raise ValueError("invalid retry configuration")
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(output.name + ".part")
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(url) as response, partial.open("wb") as f:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
            partial.replace(output)
            return
        except (OSError, urllib.error.URLError):
            partial.unlink(missing_ok=True)
            if attempt + 1 == attempts:
                raise
            time.sleep(backoff_seconds * (2 ** attempt))


def download_index(output: Path) -> Path:
    owner, slug = INDEX_REF.split("/", 1)
    url = f"{DATASET_API}/download/{owner}/{slug}/manifest.csv"
    download(url, output)
    return output


def load_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def list_dataset_files(owner: str, slug: str, page_token: str = "") -> dict:
    query = f"?pageToken={urllib.parse.quote(page_token)}" if page_token else ""
    return read_json(f"{DATASET_API}/list/{owner}/{slug}{query}")


def list_dataset_files_kaggle(
    owner: str,
    slug: str,
    page_token: str = "",
    *,
    page_size: int = 200,
    api_client=None,
) -> dict:
    if not 1 <= page_size <= 200:
        raise ValueError("page_size must be between 1 and 200")
    if api_client is None:
        import kaggle

        api_client = kaggle.api

    response = api_client.dataset_list_files(
        f"{owner}/{slug}",
        page_token=page_token or None,
        page_size=page_size,
    )
    return {
        "datasetFiles": [
            {"name": item.name, "totalBytes": int(item.total_bytes or 0)}
            for item in response.files
        ],
        "nextPageToken": str(response.next_page_token or ""),
    }


def collect_dataset_files(
    owner: str,
    slug: str,
    *,
    max_pages: int = 1,
    sleep_seconds: float = 0.0,
    page_loader: Callable[[str, str, str], dict] = list_dataset_files,
) -> list[dict]:
    if max_pages <= 0:
        raise ValueError("max_pages must be positive")
    if sleep_seconds < 0:
        raise ValueError("sleep_seconds must be nonnegative")
    files: list[dict] = []
    token = ""
    seen_tokens: set[str] = set()
    for page_index in range(max_pages):
        listing = page_loader(owner, slug, token)
        if listing.get("hasErrorMessage") or listing.get("errorMessage"):
            raise RuntimeError(f"dataset listing failed: {listing.get('errorMessage')}")
        page_files = listing.get("datasetFiles") or []
        if not isinstance(page_files, list):
            raise ValueError("datasetFiles must be a list")
        files.extend(item for item in page_files if isinstance(item, dict))
        next_token = str(listing.get("nextPageTokenNullable") or listing.get("nextPageToken") or "")
        if not next_token:
            break
        if next_token in seen_tokens:
            raise RuntimeError("dataset listing repeated a page token")
        seen_tokens.add(next_token)
        token = next_token
        if page_index + 1 < max_pages and sleep_seconds:
            time.sleep(sleep_seconds)
    return files


def choose_files(files: list[dict], count: int, selection: str) -> list[dict]:
    if count < 0:
        raise ValueError("count must be nonnegative")
    if selection == "first" or count >= len(files):
        return files[:count]
    if selection != "even":
        raise ValueError(f"unknown selection strategy: {selection}")
    if count == 0:
        return []
    if count == 1:
        return [files[len(files) // 2]]
    indices = [(index * (len(files) - 1)) // (count - 1) for index in range(count)]
    return [files[index] for index in indices]


def choose_score_ranked_files(
    files: list[dict],
    episode_manifest: list[dict[str, str]],
    count: int,
    metric: str,
) -> list[dict]:
    if count < 0:
        raise ValueError("count must be nonnegative")
    if metric not in {"avg_score", "min_score"}:
        raise ValueError(f"unsupported score metric: {metric}")

    files_by_name = {
        str(item.get("name")): item
        for item in files
        if isinstance(item.get("name"), str)
    }
    ranked: list[tuple[float, int, dict]] = []
    for row in episode_manifest:
        episode_id = str(row.get("episode_id") or "").strip()
        item = files_by_name.get(f"{episode_id}.json")
        if item is None:
            continue
        try:
            score = float(row[metric])
        except (KeyError, TypeError, ValueError):
            continue
        try:
            episode_sort = int(episode_id)
        except ValueError:
            episode_sort = -1
        ranked.append((score, episode_sort, item))

    ranked.sort(key=lambda value: (value[0], value[1]), reverse=True)
    return [item for _, _, item in ranked[:count]]


def choose_dataset(manifest: list[dict[str, str]], date: str) -> dict[str, str]:
    if date == "latest":
        return manifest[-1]
    for row in manifest:
        if row["date"] == date:
            return row
    raise ValueError(f"Date {date!r} not found in manifest.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download a small sample of public top episode JSON files.")
    parser.add_argument("--date", default="latest", help="YYYY-MM-DD or latest.")
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--max-mb", type=float, default=20.0, help="Maximum total download size.")
    parser.add_argument("--list-pages", type=int, default=1, help="Dataset file-list pages to inspect.")
    parser.add_argument("--list-sleep", type=float, default=0.1, help="Delay between file-list requests.")
    parser.add_argument("--listing-backend", choices=("kaggle", "public"), default="kaggle")
    parser.add_argument("--page-size", type=int, default=200, help="Files per authenticated listing page.")
    parser.add_argument(
        "--selection",
        choices=("first", "even", "top-avg-score", "top-min-score"),
        default="first",
    )
    parser.add_argument("--index", type=Path, default=Path("infrastructure/data/episodes_index/manifest.csv"))
    parser.add_argument("--out-root", type=Path, default=Path("infrastructure/data/episodes"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.index.exists():
        download_index(args.index)

    manifest = load_manifest(args.index)
    dataset = choose_dataset(manifest, args.date)
    owner = "kaggle"
    slug = dataset["daily_dataset_slug"]
    if args.listing_backend == "kaggle":
        page_loader = lambda owner, slug, token: list_dataset_files_kaggle(
            owner, slug, token, page_size=args.page_size
        )
    else:
        page_loader = list_dataset_files
    files = collect_dataset_files(
        owner,
        slug,
        max_pages=args.list_pages,
        sleep_seconds=args.list_sleep,
        page_loader=page_loader,
    )
    output_dir = args.out_root / f"{dataset['date']}-sample"
    if args.selection.startswith("top-"):
        daily_manifest_path = output_dir / "manifest.csv"
        daily_manifest_item = next(
            (item for item in files if item.get("name") == "manifest.csv"),
            None,
        )
        if daily_manifest_item is None:
            raise RuntimeError("daily dataset does not contain manifest.csv")
        daily_manifest_size = int(daily_manifest_item.get("totalBytes") or 0)
        if not (
            daily_manifest_path.is_file()
            and daily_manifest_path.stat().st_size == daily_manifest_size
        ):
            daily_manifest_url = (
                f"{DATASET_API}/download/{owner}/{slug}/manifest.csv"
            )
            download(daily_manifest_url, daily_manifest_path)
        metric = "avg_score" if args.selection == "top-avg-score" else "min_score"
        selected = choose_score_ranked_files(
            files,
            load_manifest(daily_manifest_path),
            args.count,
            metric,
        )
        if len(selected) < args.count:
            raise RuntimeError(
                f"only {len(selected)} score-ranked episode files were available "
                f"for requested count {args.count}"
            )
    else:
        selected = choose_files(files, args.count, args.selection)

    max_bytes = int(args.max_mb * 1024 * 1024)
    total = 0
    downloaded = 0
    for item in selected:
        name = item["name"]
        size = int(item.get("totalBytes") or 0)
        if total + size > max_bytes:
            continue
        url = f"{DATASET_API}/download/{owner}/{slug}/{urllib.parse.quote(name)}"
        output = output_dir / name
        if output.is_file() and output.stat().st_size == size:
            print(f"Cached {output} ({size} bytes)")
        else:
            download(url, output)
            print(f"Downloaded {output} ({output.stat().st_size} bytes)")
        total += output.stat().st_size
        downloaded += 1

    print(
        f"Downloaded or reused {downloaded} of {len(selected)} selected files "
        f"from {len(files)} listed files in {slug} into {output_dir}"
    )


if __name__ == "__main__":
    main()
