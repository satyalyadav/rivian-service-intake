"""Input validation and limits for untrusted transcript and vehicle fields."""

from __future__ import annotations

from collections.abc import Mapping


VEHICLE_FIELD_LIMITS = {"vin": 32, "model": 64, "year": 4, "mileage": 12}
VEHICLE_FIELD_LABELS = {"vin": "VIN", "model": "model", "year": "year", "mileage": "mileage"}
MAX_VEHICLE_TOTAL_CHARS = 128


def validate_vehicle(vehicle: object) -> dict[str, str]:
    if vehicle is None:
        return {}
    if not isinstance(vehicle, Mapping):
        raise ValueError("Vehicle context must be a dictionary of text values.")
    if len(vehicle) > len(VEHICLE_FIELD_LIMITS):
        raise ValueError("Vehicle context has too many fields.")
    normalized: dict[str, str] = {}
    for field, value in vehicle.items():
        if field not in VEHICLE_FIELD_LIMITS:
            raise ValueError("Vehicle context contains an unsupported field.")
        if not isinstance(value, str):
            raise ValueError("Vehicle values must be text.")
        if len(value) > VEHICLE_FIELD_LIMITS[field]:
            raise ValueError(
                f"Vehicle {VEHICLE_FIELD_LABELS[field]} exceeds its "
                f"{VEHICLE_FIELD_LIMITS[field]} character limit."
            )
        if value.strip():
            normalized[field] = value
    if sum(len(field) + len(value) for field, value in normalized.items()) > MAX_VEHICLE_TOTAL_CHARS:
        raise ValueError("Vehicle context exceeds the total character limit.")
    return normalized
