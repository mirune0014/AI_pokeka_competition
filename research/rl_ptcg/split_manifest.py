"""Deterministic, leakage-audited splits for Gold replay decision data."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import blake2b, sha256
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = "gold_replay_split.v1"
SPLITS = ("train", "development", "blind", "policy_family_holdout")
PROTECTED_FIELDS = (
    "episode_id",
    "submission_version",
    "style_family",
    "date_period",
    "seed",
    "deck_variant",
)
DEFAULT_COMPONENT_FIELDS = (
    "episode_id",
    "submission_version",
    "seed",
    "deck_variant",
)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _digest(value: Any, *, size: int = 32) -> str:
    return blake2b(_canonical_bytes(value), digest_size=size).hexdigest()


def _manifest_hash(manifest: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    return sha256(_canonical_bytes(payload)).hexdigest()


@dataclass(frozen=True)
class SplitItem:
    item_id: str
    episode_id: str
    submission_version: str
    style_family: str
    date_period: str
    seed: str
    deck_variant: str
    archetype: str | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "SplitItem":
        if not isinstance(value, Mapping):
            raise TypeError("split items must be mappings or SplitItem values")
        names = set(cls.__dataclass_fields__)
        data = {name: value.get(name) for name in names}
        return cls(**data)

    def validate(self) -> None:
        if not self.item_id:
            raise ValueError("split item_id must be non-empty")
        for name in PROTECTED_FIELDS:
            value = getattr(self, name)
            if value is None or not str(value).strip():
                raise ValueError(f"split item {self.item_id!r} is missing protected field {name}")

    def normalized(self) -> "SplitItem":
        self.validate()
        return SplitItem(**{
            name: None if value is None else str(value)
            for name, value in asdict(self).items()
        })


class _UnionFind:
    def __init__(self, keys: Iterable[str]):
        self.parent = {key: key for key in keys}

    def find(self, key: str) -> str:
        parent = self.parent[key]
        if parent != key:
            self.parent[key] = self.find(parent)
        return self.parent[key]

    def union(self, left: str, right: str) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root == right_root:
            return
        low, high = sorted((left_root, right_root))
        self.parent[high] = low


def _component_fields(values: Iterable[str]) -> tuple[str, ...]:
    fields = tuple(str(value) for value in values)
    if not fields or len(set(fields)) != len(fields):
        raise ValueError("component_fields must contain unique protected field names")
    unknown = sorted(set(fields) - set(PROTECTED_FIELDS))
    if unknown:
        raise ValueError(f"unknown component_fields: {unknown}")
    return fields


def _components(items: list[SplitItem], component_fields: tuple[str, ...]) -> list[list[SplitItem]]:
    union = _UnionFind(item.item_id for item in items)
    first_by_token: dict[tuple[str, str], str] = {}
    for item in items:
        for field in component_fields:
            token = (field, str(getattr(item, field)))
            first = first_by_token.setdefault(token, item.item_id)
            union.union(first, item.item_id)
    grouped: dict[str, list[SplitItem]] = {}
    for item in items:
        grouped.setdefault(union.find(item.item_id), []).append(item)
    return sorted(
        (sorted(group, key=lambda item: item.item_id) for group in grouped.values()),
        key=lambda group: group[0].item_id,
    )


def _protected_values(group: list[SplitItem]) -> dict[str, list[str]]:
    return {
        field: sorted({str(getattr(item, field)) for item in group})
        for field in PROTECTED_FIELDS
    }


def _unit_interval(seed: str, component_id: str) -> float:
    raw = blake2b(f"{seed}\0{component_id}".encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(raw, "big") / float(1 << 64)


def _assignment(
    fraction: float,
    *,
    blind_fraction: float,
    development_fraction: float,
) -> str:
    if fraction < blind_fraction:
        return "blind"
    if fraction < blind_fraction + development_fraction:
        return "development"
    return "train"


def _field_overlaps(item_rows: list[dict[str, Any]], fields: Iterable[str]) -> dict[str, dict[str, list[str]]]:
    overlaps: dict[str, dict[str, list[str]]] = {}
    for field in fields:
        split_by_value: dict[str, set[str]] = {}
        for row in item_rows:
            split_by_value.setdefault(str(row[field]), set()).add(str(row["split"]))
        collisions = {
            value: sorted(splits)
            for value, splits in split_by_value.items()
            if len(splits) > 1
        }
        if collisions:
            overlaps[field] = collisions
    return overlaps


def _reserved_value_audit(
    item_rows: list[dict[str, Any]],
    *,
    field: str,
    values: set[str],
    expected_split: str,
) -> dict[str, Any]:
    observed: dict[str, list[str]] = {}
    for value in sorted(values):
        splits = sorted({str(row["split"]) for row in item_rows if str(row[field]) == value})
        if splits:
            observed[value] = splits
    violations = {value: splits for value, splits in observed.items() if splits != [expected_split]}
    return {"passed": not violations, "expected_split": expected_split, "observed": observed, "violations": violations}


def _overlap_audit(
    item_rows: list[dict[str, Any]],
    *,
    component_fields: tuple[str, ...],
    holdout_styles: set[str],
    blind_dates: set[str],
    development_dates: set[str],
    legacy_format: bool,
) -> dict[str, Any]:
    if legacy_format:
        overlaps = _field_overlaps(item_rows, PROTECTED_FIELDS)
        return {"passed": not overlaps, "overlaps": overlaps}
    enforced = _field_overlaps(item_rows, component_fields)
    informational = _field_overlaps(
        item_rows,
        (field for field in PROTECTED_FIELDS if field not in component_fields),
    )
    style_audit = _reserved_value_audit(
        item_rows, field="style_family", values=holdout_styles, expected_split="policy_family_holdout",
    )
    blind_date_audit = _reserved_value_audit(
        item_rows, field="date_period", values=blind_dates, expected_split="blind",
    )
    development_date_audit = _reserved_value_audit(
        item_rows, field="date_period", values=development_dates, expected_split="development",
    )
    passed = not enforced and style_audit["passed"] and blind_date_audit["passed"] and development_date_audit["passed"]
    return {
        "passed": passed,
        "enforced_component_fields": list(component_fields),
        "enforced_overlaps": enforced,
        "informational_overlap_counts": {
            field: len(values) for field, values in sorted(informational.items())
        },
        "policy_family_holdout": style_audit,
        "blind_date_periods": blind_date_audit,
        "development_date_periods": development_date_audit,
    }


def build_split_manifest(
    values: Iterable[SplitItem | Mapping[str, Any]],
    *,
    source_dataset_sha256: str,
    seed: str,
    development_fraction: float = 0.15,
    blind_fraction: float = 0.15,
    holdout_style_families: Iterable[str] = (),
    blind_date_periods: Iterable[str] = (),
    development_date_periods: Iterable[str] = (),
    component_fields: Iterable[str] = DEFAULT_COMPONENT_FIELDS,
) -> dict[str, Any]:
    """Build a stable split manifest without decision-level randomization.

    Episode/submission/seed/deck components are atomic by default. Style-family
    and time generalization use explicit holdout reservations, avoiding the
    degenerate all-data component produced by connecting every shared date or
    style value.
    """
    return _build_split_manifest(
        values,
        source_dataset_sha256=source_dataset_sha256,
        seed=seed,
        development_fraction=development_fraction,
        blind_fraction=blind_fraction,
        holdout_style_families=holdout_style_families,
        blind_date_periods=blind_date_periods,
        development_date_periods=development_date_periods,
        component_fields=component_fields,
        legacy_format=False,
    )


def _build_split_manifest(
    values: Iterable[SplitItem | Mapping[str, Any]],
    *,
    source_dataset_sha256: str,
    seed: str,
    development_fraction: float,
    blind_fraction: float,
    holdout_style_families: Iterable[str],
    blind_date_periods: Iterable[str],
    development_date_periods: Iterable[str],
    component_fields: Iterable[str],
    legacy_format: bool,
) -> dict[str, Any]:
    if len(source_dataset_sha256) != 64 or any(character not in "0123456789abcdefABCDEF" for character in source_dataset_sha256):
        raise ValueError("source_dataset_sha256 must be a 64-character hexadecimal SHA256")
    if not seed:
        raise ValueError("split seed must be non-empty")
    if not 0.0 <= development_fraction <= 1.0 or not 0.0 <= blind_fraction <= 1.0:
        raise ValueError("split fractions must be between zero and one")
    if development_fraction + blind_fraction > 1.0:
        raise ValueError("development_fraction + blind_fraction must not exceed one")
    components_by = _component_fields(component_fields)
    holdouts = {str(value) for value in holdout_style_families}
    blind_dates = {str(value) for value in blind_date_periods}
    development_dates = {str(value) for value in development_date_periods}
    overlap_dates = sorted(blind_dates & development_dates)
    if overlap_dates:
        raise ValueError(f"date periods cannot be both blind and development: {overlap_dates}")

    items = [
        (value if isinstance(value, SplitItem) else SplitItem.from_mapping(value)).normalized()
        for value in values
    ]
    if not items:
        raise ValueError("cannot split an empty dataset")
    ids = [item.item_id for item in items]
    if len(set(ids)) != len(ids):
        raise ValueError("split item_id values must be unique")
    items.sort(key=lambda item: item.item_id)
    item_rows: list[dict[str, Any]] = []
    component_rows: list[dict[str, Any]] = []
    for group in _components(items, components_by):
        protected = _protected_values(group)
        identity = {"items": [item.item_id for item in group], "protected": protected}
        if not legacy_format:
            identity["component_fields"] = list(components_by)
        component_id = _digest(identity)
        fraction = _unit_interval(str(seed), component_id)
        is_holdout = bool(holdouts.intersection(protected["style_family"]))
        is_blind_date = bool(blind_dates.intersection(protected["date_period"]))
        is_development_date = bool(development_dates.intersection(protected["date_period"]))
        reservations = sum((is_holdout, is_blind_date, is_development_date))
        if reservations > 1:
            raise ValueError(
                f"component {component_id} intersects multiple reserved holdouts; choose disjoint style/date groups"
            )
        if is_holdout:
            split, reason = "policy_family_holdout", "reserved_style_family"
        elif is_blind_date:
            split, reason = "blind", "reserved_date_period"
        elif is_development_date:
            split, reason = "development", "reserved_date_period"
        else:
            split, reason = _assignment(
                fraction,
                blind_fraction=blind_fraction,
                development_fraction=development_fraction,
            ), "stable_hash_threshold"
        component_row = {
            "component_id": component_id,
            "split": split,
            "assignment_fraction": format(fraction, ".17g"),
            "item_ids": [item.item_id for item in group],
            "protected_values": protected,
        }
        if not legacy_format:
            component_row["assignment_reason"] = reason
        component_rows.append(component_row)
        for item in group:
            row = asdict(item)
            row.update({"component_id": component_id, "split": split})
            item_rows.append(row)

    item_rows.sort(key=lambda row: row["item_id"])
    component_rows.sort(key=lambda row: row["component_id"])
    audit = _overlap_audit(
        item_rows,
        component_fields=components_by,
        holdout_styles=holdouts,
        blind_dates=blind_dates,
        development_dates=development_dates,
        legacy_format=legacy_format,
    )
    if not audit["passed"]:
        raise AssertionError("internal error: protected values crossed split boundaries")
    split_counts = {
        split: sum(1 for row in item_rows if row["split"] == split)
        for split in SPLITS
    }
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "algorithm": (
            "protected-connected-components-blake2b-threshold-v1"
            if legacy_format
            else "configured-components-reserved-holdouts-blake2b-v2"
        ),
        "source_dataset_sha256": source_dataset_sha256.lower(),
        "seed": str(seed),
        "development_fraction": development_fraction,
        "blind_fraction": blind_fraction,
        "holdout_style_families": sorted(holdouts),
        "protected_fields": list(PROTECTED_FIELDS),
        "item_count": len(item_rows),
        "component_count": len(component_rows),
        "split_counts": split_counts,
        "overlap_audit": audit,
        "items": item_rows,
        "components": component_rows,
    }
    if not legacy_format:
        manifest["component_fields"] = list(components_by)
        manifest["blind_date_periods"] = sorted(blind_dates)
        manifest["development_date_periods"] = sorted(development_dates)
    manifest["manifest_sha256"] = _manifest_hash(manifest)
    return manifest


def validate_split_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(manifest, Mapping) or manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported split manifest schema")
    expected_hash = _manifest_hash(manifest)
    if manifest.get("manifest_sha256") != expected_hash:
        raise ValueError("split manifest SHA256 does not validate")
    try:
        legacy_format = "component_fields" not in manifest
        rebuilt = _build_split_manifest(
            manifest["items"],
            source_dataset_sha256=str(manifest["source_dataset_sha256"]),
            seed=str(manifest["seed"]),
            development_fraction=float(manifest["development_fraction"]),
            blind_fraction=float(manifest["blind_fraction"]),
            holdout_style_families=manifest["holdout_style_families"],
            blind_date_periods=() if legacy_format else manifest["blind_date_periods"],
            development_date_periods=() if legacy_format else manifest["development_date_periods"],
            component_fields=PROTECTED_FIELDS if legacy_format else manifest["component_fields"],
            legacy_format=legacy_format,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"invalid split manifest content: {error}") from error
    if dict(manifest) != rebuilt:
        raise ValueError("split manifest content is not reproducible")
    return rebuilt


def write_split_manifest(path: str | Path, manifest: Mapping[str, Any]) -> None:
    """Write once; an existing blind manifest may only be reused unchanged."""
    validated = validate_split_manifest(manifest)
    destination = Path(path)
    if destination.exists():
        existing = load_split_manifest(destination)
        if existing != validated:
            raise FileExistsError(f"refusing to replace frozen split manifest: {destination}")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(validated, indent=2, sort_keys=True) + "\n", encoding="ascii")


def load_split_manifest(path: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="ascii"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"could not read split manifest: {error}") from error
    return validate_split_manifest(value)
