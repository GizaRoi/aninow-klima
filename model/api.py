"""Stateless HTTP API over the rules model.

Run from model/: uvicorn api:app --host 0.0.0.0 --port 8000 --workers 1
Each request runs the CLI in its own process and temp file.
"""
from __future__ import annotations

import csv
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path
from threading import BoundedSemaphore
from typing import Any, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from starlette.exceptions import HTTPException as StarletteHTTPException

HERE = Path(__file__).resolve().parent
CONTRACT_VERSION = "klima-comparison.v1"
LOGGER = logging.getLogger("klima.api")
MODEL_TIMEOUT_SECONDS = 120
MODEL_SLOT = BoundedSemaphore(1)
DEFAULT_CORS_ORIGINS = (
    "https://aninow-klima.vercel.app", "http://localhost:3000", "http://127.0.0.1:3000",
    "http://localhost:4173", "http://127.0.0.1:4173",
)


def read_rows(filename: str) -> list[dict[str, str]]:
    with (HERE / filename).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


PLACES = {f"{row['place']}, {row['province']}": row for row in read_rows("places.csv")}
CROPS = {row["crop"]: row for row in read_rows("crops.csv")}


def model_version() -> str:
    """sha256 over the engine and its committed input files."""
    digest = hashlib.sha256()
    files = sorted({HERE / "klima_model.py", *HERE.glob("*.csv"), *HERE.glob("*.txt")})
    for path in files:
        if path.name.startswith("requirements"):
            continue
        digest.update(path.name.encode("utf-8") + b"\0")
        digest.update(path.read_bytes())
    return "sha256:" + digest.hexdigest()


MODEL_VERSION = model_version()
Water = Literal["rain", "irrigation"]
Priority = Literal["balanced", "saving_water", "healthier_soil", "finishing_early"]


class ComparisonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, json_schema_extra={
        "examples": [{"place": "Science City of Muñoz, Nueva Ecija", "harvest": "2026-11-15",
                      "next_planting": "2027-05-31", "drainage": "well_drained",
                      "main_crop": "rice", "water": "rain", "priority": "balanced"}]})

    place: str = Field(min_length=1, max_length=150)
    harvest: date
    next_planting: date
    drainage: Literal["well_drained", "poorly_drained", "unknown"]
    main_crop: str = Field(default="rice", min_length=1, max_length=40)
    water: Water = "rain"
    priority: Priority = "balanced"
    soil_ph: float | None = Field(default=None, ge=3, le=10, strict=True)
    soil_texture: Literal["light", "medium", "heavy"] | None = None
    prep_days: int = Field(default=0, ge=0, le=180, strict=True)
    picking_days: int = Field(default=0, ge=0, le=180, strict=True)
    turnaround_days: int = Field(default=0, ge=0, le=90, strict=True)
    pass_mark: float = Field(default=0.6, ge=0, le=1, strict=True)

    @field_validator("place")
    @classmethod
    def supported_place(cls, value: str) -> str:
        if value not in PLACES:
            raise ValueError("Choose a supported place from /api/v1/catalog.")
        return value

    @field_validator("main_crop")
    @classmethod
    def supported_crop(cls, value: str) -> str:
        if value != "fallow" and value not in CROPS:
            raise ValueError("Choose a supported crop from /api/v1/catalog.")
        return value

    @field_validator("harvest", "next_planting", mode="before")
    @classmethod
    def calendar_date(cls, value: Any) -> Any:
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("Use a calendar date in YYYY-MM-DD format.")
        parsed = date.fromisoformat(value)
        if (parsed.month, parsed.day) == (2, 29):
            raise ValueError("February 29 cannot be replayed across non-leap historical years.")
        return parsed

    @model_validator(mode="after")
    def planting_window(self) -> ComparisonRequest:
        if self.next_planting <= self.harvest:
            raise ValueError("Next planting must be after harvest.")
        harvest_md = (self.harvest.month, self.harvest.day)
        next_md = (self.next_planting.month, self.next_planting.day)
        expected_year = self.harvest.year + (next_md <= harvest_md)
        if self.next_planting.year != expected_year:
            raise ValueError("The model supports one annual planting window, not multiple years.")
        return self

    def cli_args(self) -> list[str]:
        place = PLACES[self.place]
        args = [sys.executable, str(HERE / "klima_model.py"),
                "--place", self.place, "--province", place["province"],
                "--lat", place["latitude"], "--lon", place["longitude"],
                "--harvest", self.harvest.isoformat(),
                "--next-planting", self.next_planting.isoformat(),
                "--main-crop", self.main_crop, "--drainage", self.drainage,
                "--prep-days", str(self.prep_days), "--picking-days", str(self.picking_days),
                "--turnaround-days", str(self.turnaround_days),
                "--pass-mark", str(self.pass_mark)]
        if self.soil_ph is not None:
            args += ["--soil-ph", str(self.soil_ph)]
        if self.soil_texture is not None:
            args += ["--soil-texture", self.soil_texture]
        return args


class ComparisonResponse(BaseModel):
    contract_version: str
    mode: Literal["rules_model"]
    model_version: str
    request_id: str
    inputs: ComparisonRequest
    ranking: list[str]
    warnings: list[str]
    results: dict[str, Any]


class ErrorBody(BaseModel):
    code: str
    message: str
    field_errors: dict[str, list[str]]


class ErrorResponse(BaseModel):
    error: ErrorBody
    request_id: str


def run_comparison(payload: ComparisonRequest) -> dict[str, Any]:
    # own temp dir per request; never mutate model globals
    with tempfile.TemporaryDirectory(prefix="klima-api-") as directory:
        output = Path(directory) / "results.json"
        process = subprocess.run(
            payload.cli_args() + ["--quiet", "--out", str(output)],
            cwd=HERE, capture_output=True, text=True, encoding="utf-8",
            timeout=MODEL_TIMEOUT_SECONDS, check=False,
        )
        if process.returncode:
            LOGGER.error("Model exited %s: %s", process.returncode, process.stderr[-2000:])
            raise RuntimeError("Model process failed.")
        with output.open(encoding="utf-8") as stream:
            return json.load(stream)


def error_response(request: Request, status: int, code: str, message: str,
                   fields: dict | None = None, headers: dict | None = None) -> JSONResponse:
    return JSONResponse(status_code=status, headers=headers, content={
        "error": {"code": code, "message": message, "field_errors": fields or {}},
        "request_id": request.state.request_id,
    })


def create_app(origins: list[str] | None = None) -> FastAPI:
    app = FastAPI(title="AniNow Klima comparison API", version="1.0.0",
                  description="Historical rules-model comparisons, without persistence or yield predictions.",
                  responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse},
                             504: {"model": ErrorResponse}})
    if origins is None:
        origins = [value.strip() for value in os.getenv(
            "CORS_ORIGINS", ",".join(DEFAULT_CORS_ORIGINS)).split(",") if value.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins,
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type"],
                       expose_headers=["X-Request-ID", "Retry-After"])

    @app.middleware("http")
    async def request_identity(request: Request, call_next):
        request.state.request_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError):
        fields: dict[str, list[str]] = {}
        for error in exc.errors():
            key = ".".join(str(part) for part in error["loc"] if part != "body") or "body"
            fields.setdefault(key, []).append(error["msg"])
        return error_response(request, 422, "invalid_inputs", "Check the submitted field inputs.", fields)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        codes = {404: "not_found", 405: "method_not_allowed", 503: "model_unavailable",
                 504: "model_timeout"}
        return error_response(request, exc.status_code, codes.get(exc.status_code, "request_failed"),
                              str(exc.detail), headers=exc.headers)

    @app.get("/", include_in_schema=False, response_class=RedirectResponse)
    def index():
        return RedirectResponse("https://aninow-klima.vercel.app/", status_code=307)

    @app.get("/health")
    def health():
        return {"status": "ok", "contract_version": CONTRACT_VERSION, "model_version": MODEL_VERSION}

    @app.get("/api/v1/catalog")
    def catalog():
        return {"contract_version": CONTRACT_VERSION, "model_version": MODEL_VERSION,
                "places": [{"id": key, "name": row["place"], "province": row["province"]}
                           for key, row in PLACES.items()],
                "crops": [{"id": key, "name": row["english_name"], "local_name": row["local_name"],
                           "limits_basis": row["limits"]} for key, row in CROPS.items()],
                "capabilities": ["fallow", "whole_schedule"],
                "drainage": ["well_drained", "poorly_drained", "unknown"],
                "soil_texture": ["light", "medium", "heavy"],
                "water": ["rain", "irrigation"],
                "priorities": ["balanced", "saving_water", "healthier_soil", "finishing_early"],
                "season_groups": ["all", "normal", "dry", "el_nino"]}

    @app.post("/api/v1/compare", response_model=ComparisonResponse)
    def compare(payload: ComparisonRequest, request: Request):
        if not MODEL_SLOT.acquire(blocking=False):
            raise HTTPException(503, "The model is busy. Please retry shortly.", headers={"Retry-After": "5"})
        try:
            try:
                results = run_comparison(payload)
                ranking = results["fields"][payload.water]["rankings"][payload.priority]
            except subprocess.TimeoutExpired:
                raise HTTPException(504, "The calculation timed out. Please try again.") from None
            except (OSError, ValueError, RuntimeError, KeyError):
                LOGGER.exception("Model calculation failed for request %s", request.state.request_id)
                raise HTTPException(503, "The model could not calculate this comparison. Please try again.") from None
        finally:
            MODEL_SLOT.release()
        warnings = [
            "Historical season counts are not forecasts or probabilities of crop success.",
            "This rules model has no validated yield, profit or predictive accuracy estimates.",
            "Only the Muñoz results have been reviewed in detail; other places have data coverage tests.",
            "Rankings use all historical seasons and the shortest cycle; changing the season view does not rerank crops.",
        ]
        if payload.water == "irrigation":
            warnings.append("The irrigation scenario assumes sufficient water, not a measured irrigation supply.")
        if payload.drainage == "unknown":
            warnings.append("Drainage is unknown. Confirm it before treating a drained-soil crop as feasible.")
        return jsonable_encoder({"contract_version": CONTRACT_VERSION, "mode": "rules_model",
                                 "model_version": MODEL_VERSION, "request_id": request.state.request_id,
                                 "inputs": payload, "ranking": ranking, "warnings": warnings, "results": results})

    return app


app = create_app()
