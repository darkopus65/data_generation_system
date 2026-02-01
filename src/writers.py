"""Output writers for JSONL and Parquet formats."""

import gzip
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pyarrow as pa
import pyarrow.parquet as pq

from .models import Event
from .config import SimulationConfig


class JSONLWriter:
    """Writer for JSONL output format."""

    def __init__(
        self,
        output_path: Path,
        compress: bool = True,
        batch_size: int = 10000,
    ):
        self.output_path = output_path
        self.compress = compress
        self.batch_size = batch_size
        self.buffer: list[dict] = []
        self.total_written = 0
        self._file = None

    def __enter__(self):
        self._open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _open(self):
        """Open the output file."""
        if self.compress:
            self._file = gzip.open(self.output_path, "wt", encoding="utf-8")
        else:
            self._file = open(self.output_path, "w", encoding="utf-8")

    def write_event(self, event: Event) -> None:
        """Add event to buffer, flush if full."""
        self.buffer.append(event.to_dict())

        if len(self.buffer) >= self.batch_size:
            self._flush()

    def write_events(self, events: list[Event]) -> None:
        """Write multiple events."""
        for event in events:
            self.write_event(event)

    def _flush(self) -> None:
        """Write buffer to file."""
        if not self.buffer:
            return

        for event_dict in self.buffer:
            line = json.dumps(event_dict, ensure_ascii=False)
            self._file.write(line + "\n")

        self.total_written += len(self.buffer)
        self.buffer = []

    def close(self) -> None:
        """Flush remaining events and close file."""
        self._flush()
        if self._file:
            self._file.close()
            self._file = None


class ParquetWriter:
    """Writer for Parquet output format."""

    # Schema for flat Parquet output
    SCHEMA = pa.schema([
        ("event_id", pa.string()),
        ("event_name", pa.string()),
        ("event_timestamp", pa.timestamp("us")),
        ("user_id", pa.string()),
        ("session_id", pa.string()),
        ("device_id", pa.string()),
        ("platform", pa.string()),
        ("os_version", pa.string()),
        ("app_version", pa.string()),
        ("device_model", pa.string()),
        ("country", pa.string()),
        ("language", pa.string()),
        ("player_level", pa.int32()),
        ("vip_level", pa.int32()),
        ("total_spent_usd", pa.float32()),
        ("days_since_install", pa.int32()),
        ("cohort_date", pa.string()),
        ("current_chapter", pa.int32()),
        ("ab_tests", pa.string()),  # JSON string
        ("event_properties", pa.string()),  # JSON string
    ])

    def __init__(
        self,
        output_path: Path,
        batch_size: int = 100000,
    ):
        self.output_path = output_path
        self.batch_size = batch_size
        self.buffer: list[dict] = []
        self.total_written = 0
        self._writer: Optional[pq.ParquetWriter] = None

    def __enter__(self):
        self._open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _open(self):
        """Open the Parquet writer."""
        self._writer = pq.ParquetWriter(
            self.output_path,
            self.SCHEMA,
            compression="snappy",
        )

    def write_event(self, event: Event) -> None:
        """Add event to buffer, flush if full."""
        flat = self._flatten_event(event)
        self.buffer.append(flat)

        if len(self.buffer) >= self.batch_size:
            self._flush()

    def write_events(self, events: list[Event]) -> None:
        """Write multiple events."""
        for event in events:
            self.write_event(event)

    def _flatten_event(self, event: Event) -> dict:
        """Flatten nested event structure for Parquet."""
        event_dict = event.to_dict()

        return {
            "event_id": event_dict["event_id"],
            "event_name": event_dict["event_name"],
            "event_timestamp": datetime.fromisoformat(
                event_dict["event_timestamp"].rstrip("Z")
            ),
            "user_id": event_dict["user_id"],
            "session_id": event_dict["session_id"],
            "device_id": event_dict["device"]["device_id"],
            "platform": event_dict["device"]["platform"],
            "os_version": event_dict["device"]["os_version"],
            "app_version": event_dict["device"]["app_version"],
            "device_model": event_dict["device"]["device_model"],
            "country": event_dict["device"]["country"],
            "language": event_dict["device"]["language"],
            "player_level": event_dict["user_properties"]["player_level"],
            "vip_level": event_dict["user_properties"]["vip_level"],
            "total_spent_usd": event_dict["user_properties"]["total_spent_usd"],
            "days_since_install": event_dict["user_properties"]["days_since_install"],
            "cohort_date": event_dict["user_properties"]["cohort_date"],
            "current_chapter": event_dict["user_properties"]["current_chapter"],
            "ab_tests": json.dumps(event_dict["ab_tests"]),
            "event_properties": json.dumps(event_dict["event_properties"]),
        }

    def _flush(self) -> None:
        """Write buffer to Parquet file."""
        if not self.buffer:
            return

        # Convert to columnar format
        columns = {field.name: [] for field in self.SCHEMA}

        for row in self.buffer:
            for col_name in columns:
                columns[col_name].append(row.get(col_name))

        # Create table and write
        table = pa.table(columns, schema=self.SCHEMA)
        self._writer.write_table(table)

        self.total_written += len(self.buffer)
        self.buffer = []

    def close(self) -> None:
        """Flush remaining events and close file."""
        self._flush()
        if self._writer:
            self._writer.close()
            self._writer = None


class MetadataWriter:
    """Writer for simulation metadata."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.metadata: dict[str, Any] = {
            "generator_version": "0.1.0",
            "generated_at": None,
            "config_hash": None,
            "seed": None,
            "simulation": {},
            "stats": {
                "total_installs": 0,
                "total_events": 0,
                "unique_users": 0,
                "events_by_type": {},
                "installs_by_source": {},
                "installs_by_player_type": {},
            },
            "config_snapshot": {},
        }

    def set_config(self, config: SimulationConfig) -> None:
        """Set configuration in metadata."""
        self.metadata["seed"] = config.seed
        self.metadata["simulation"] = {
            "start_date": config.start_date,
            "end_date": None,  # Will be set at end
            "duration_days": config.duration_days,
        }
        self.metadata["config_snapshot"] = config.raw

        # Calculate config hash
        config_str = json.dumps(config.raw, sort_keys=True)
        self.metadata["config_hash"] = f"sha256:{hashlib.sha256(config_str.encode()).hexdigest()}"

    def set_generation_time(self, timestamp: datetime) -> None:
        """Set generation timestamp."""
        self.metadata["generated_at"] = timestamp.isoformat() + "Z"

    def set_end_date(self, end_date: str) -> None:
        """Set simulation end date."""
        self.metadata["simulation"]["end_date"] = end_date

    def increment_event_count(self, event_name: str, count: int = 1) -> None:
        """Increment event type counter."""
        self.metadata["stats"]["total_events"] += count
        if event_name not in self.metadata["stats"]["events_by_type"]:
            self.metadata["stats"]["events_by_type"][event_name] = 0
        self.metadata["stats"]["events_by_type"][event_name] += count

    def increment_installs(
        self,
        source: str,
        player_type: str,
        count: int = 1,
    ) -> None:
        """Increment install counters."""
        self.metadata["stats"]["total_installs"] += count
        self.metadata["stats"]["unique_users"] += count

        if source not in self.metadata["stats"]["installs_by_source"]:
            self.metadata["stats"]["installs_by_source"][source] = 0
        self.metadata["stats"]["installs_by_source"][source] += count

        if player_type not in self.metadata["stats"]["installs_by_player_type"]:
            self.metadata["stats"]["installs_by_player_type"][player_type] = 0
        self.metadata["stats"]["installs_by_player_type"][player_type] += count

    def write(self) -> Path:
        """Write metadata to file."""
        output_path = self.output_dir / "metadata.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)
        return output_path


class OutputManager:
    """Manages all output writers."""

    def __init__(
        self,
        output_dir: Path,
        output_format: str = "jsonl",
        compression: str = "gzip",
        batch_size: int = 10000,
        include_metadata: bool = True,
    ):
        self.output_dir = output_dir
        self.output_format = output_format
        self.compression = compression
        self.batch_size = batch_size
        self.include_metadata = include_metadata

        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.jsonl_writer: Optional[JSONLWriter] = None
        self.parquet_writer: Optional[ParquetWriter] = None
        self.metadata_writer: Optional[MetadataWriter] = None

        self._setup_writers()

    def _setup_writers(self):
        """Initialize writers based on output format."""
        if self.output_format in ("jsonl", "both"):
            ext = ".jsonl.gz" if self.compression == "gzip" else ".jsonl"
            jsonl_path = self.output_dir / f"events{ext}"
            self.jsonl_writer = JSONLWriter(
                jsonl_path,
                compress=(self.compression == "gzip"),
                batch_size=self.batch_size,
            )

        if self.output_format in ("parquet", "both"):
            parquet_path = self.output_dir / "events.parquet"
            self.parquet_writer = ParquetWriter(
                parquet_path,
                batch_size=self.batch_size * 10,  # Larger batches for Parquet
            )

        if self.include_metadata:
            self.metadata_writer = MetadataWriter(self.output_dir)

    def __enter__(self):
        if self.jsonl_writer:
            self.jsonl_writer._open()
        if self.parquet_writer:
            self.parquet_writer._open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def set_config(self, config: SimulationConfig) -> None:
        """Set configuration in metadata."""
        if self.metadata_writer:
            self.metadata_writer.set_config(config)

    def write_event(self, event: Event) -> None:
        """Write event to all active writers."""
        if self.jsonl_writer:
            self.jsonl_writer.write_event(event)
        if self.parquet_writer:
            self.parquet_writer.write_event(event)
        if self.metadata_writer:
            self.metadata_writer.increment_event_count(event.event_name)

    def write_events(self, events: list[Event]) -> None:
        """Write multiple events to all active writers."""
        for event in events:
            self.write_event(event)

    def record_install(self, source: str, player_type: str) -> None:
        """Record an install in metadata."""
        if self.metadata_writer:
            self.metadata_writer.increment_installs(source, player_type)

    def get_total_events(self) -> int:
        """Get total events written."""
        if self.jsonl_writer:
            return self.jsonl_writer.total_written + len(self.jsonl_writer.buffer)
        if self.parquet_writer:
            return self.parquet_writer.total_written + len(self.parquet_writer.buffer)
        return 0

    def close(self) -> None:
        """Close all writers."""
        if self.jsonl_writer:
            self.jsonl_writer.close()
        if self.parquet_writer:
            self.parquet_writer.close()

    def finalize(self, end_date: str, generation_time: datetime) -> None:
        """Finalize output and write metadata."""
        if self.metadata_writer:
            self.metadata_writer.set_end_date(end_date)
            self.metadata_writer.set_generation_time(generation_time)
            self.metadata_writer.write()
