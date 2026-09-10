"""
Resolves an IPv4 address to a coarse (country, asn) pair using the same
DB-IP Lite CSV snapshots mirage-core already maintains
(mirage-core/data/geo/, see its SOURCE.md) -- mounted read-only into this
container rather than duplicated, since both sensors run on the same box.

Deliberately offline and range-based (bisect over sorted CSV rows), not a
live geo-IP API call: no per-request network dependency, no rate limit, no
new failure mode if a third-party API is down. Ported from mirage-core's
scripts/geo_lookup.py -- same approach, trimmed to what mirage-mcp needs.

The raw IP is never persisted (see capture.py): this module and the caller
in server.py only ever produce a country code and an HMAC of the IP, both
computed before the address itself is discarded.
"""

import bisect
import ipaddress
from dataclasses import dataclass
from pathlib import Path

UNKNOWN_COUNTRY_CODE = "ZZ"


@dataclass
class GeoResult:
    country: str | None
    asn: str | None


class GeoLookup:
    def __init__(self, asn_csv_path: str, country_csv_path: str):
        self.asn_csv_path = Path(asn_csv_path)
        self.country_csv_path = Path(country_csv_path)

        self._asn_starts: list[int] = []
        self._asn_rows: list[tuple] = []  # (start_int, end_int, asn)

        self._country_starts: list[int] = []
        self._country_rows: list[tuple] = []  # (start_int, end_int, country_code)

        if self.asn_csv_path.exists():
            self._load_asn()
        if self.country_csv_path.exists():
            self._load_country()

    def _load_asn(self) -> None:
        rows = []
        with open(self.asn_csv_path, newline="", encoding="utf-8") as f:
            for line in f:
                if not line or line.startswith("#"):
                    continue
                parts = line.rstrip("\n").split(",")
                if len(parts) < 3:
                    continue
                start_raw, end_raw, asn_raw = parts[0], parts[1], parts[2]
                try:
                    start_int = int(ipaddress.IPv4Address(start_raw))
                    end_int = int(ipaddress.IPv4Address(end_raw))
                except ValueError:
                    continue
                asn = f"AS{asn_raw}" if asn_raw else None
                rows.append((start_int, end_int, asn))

        rows.sort(key=lambda r: r[0])
        self._asn_rows = rows
        self._asn_starts = [r[0] for r in rows]

    def _load_country(self) -> None:
        rows = []
        with open(self.country_csv_path, newline="", encoding="utf-8") as f:
            for line in f:
                if not line or line.startswith("#"):
                    continue
                parts = line.rstrip("\n").split(",")
                if len(parts) < 3:
                    continue
                start_raw, end_raw, country_code = parts[0], parts[1], parts[2]
                try:
                    start_int = int(ipaddress.IPv4Address(start_raw))
                    end_int = int(ipaddress.IPv4Address(end_raw))
                except ValueError:
                    continue
                rows.append((start_int, end_int, country_code))

        rows.sort(key=lambda r: r[0])
        self._country_rows = rows
        self._country_starts = [r[0] for r in rows]

    def _lookup_asn(self, ip_int: int) -> str | None:
        idx = bisect.bisect_right(self._asn_starts, ip_int) - 1
        if idx < 0:
            return None
        start_int, end_int, asn = self._asn_rows[idx]
        return asn if start_int <= ip_int <= end_int else None

    def _lookup_country(self, ip_int: int) -> str | None:
        idx = bisect.bisect_right(self._country_starts, ip_int) - 1
        if idx < 0:
            return None
        start_int, end_int, country_code = self._country_rows[idx]
        if start_int <= ip_int <= end_int and country_code != UNKNOWN_COUNTRY_CODE:
            return country_code
        return None

    def lookup(self, ip: str) -> GeoResult:
        try:
            ip_int = int(ipaddress.IPv4Address(ip))
        except ValueError:
            return GeoResult(country=None, asn=None)
        return GeoResult(country=self._lookup_country(ip_int), asn=self._lookup_asn(ip_int))
