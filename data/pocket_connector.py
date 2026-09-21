import asyncio
import inspect
import json
import os
import time
from dataclasses import dataclass
from typing import Any, AsyncIterator, Iterable, Optional

from dotenv import load_dotenv
from BinaryOptionsToolsV2.pocketoption import PocketOptionAsync

from config import CONFIG


CANONICAL_GBPUSD_ASSET = "GBPUSD"


class PocketConnectionError(RuntimeError):
    """Raised when Pocket Option market-data access cannot be established."""


class PocketDataError(RuntimeError):
    """Raised when Pocket Option returns unusable market data."""


@dataclass(frozen=True, slots=True)
class MarketTick:
    timestamp: float
    price: float
    asset: str
    received_at: float
    source: str = "pocket_option"


@dataclass(frozen=True, slots=True)
class HistoricalCandle:
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    asset: str
    timeframe_seconds: int
    source: str = "pocket_option"


class PocketConnector:
    """
    Read-only Pocket Option market-data connector.

    The bot is an analyst/consultant only. This class intentionally exposes
    NO buy/sell/order methods.

    Supported local .env formats:

    1) Full SSID:
       POCKET_SSID=42["auth",...]

    2) Existing split credentials:
       POCKET_SESSION_ID=...
       POCKET_USER_ID=...
       POCKET_IS_DEMO=1

    `POCKET_SSID` takes precedence when both formats exist.
    """

    def __init__(
        self,
        asset_candidates: Iterable[str] = CONFIG.POCKET_ASSET_CANDIDATES,
    ) -> None:
        load_dotenv()

        self._ssid = self._load_ssid()
        self._asset_candidates = tuple(
            dict.fromkeys(str(x).strip() for x in asset_candidates if str(x).strip())
        )

        if not self._asset_candidates:
            raise ValueError("At least one Pocket Option asset candidate is required.")

        self._client: Optional[PocketOptionAsync] = None
        self._asset_symbol: Optional[str] = None
        self._asset_label: Optional[str] = None
        self._history_symbol: str = "GBPUSD"
        self._connected = False
        self._connect_lock = asyncio.Lock()

        self._last_error: Optional[str] = None
        self._reconnect_count = 0
        self._last_message_at: Optional[float] = None

    @property
    def asset(self) -> str:
        """Return the API symbol used by Pocket Option calls."""
        return self._asset_symbol or self.normalize_asset(self._asset_candidates[0])

    @property
    def history_asset(self) -> str:
        """Symbol dedicated to historical bootstrap requests."""
        return self._history_symbol

    @property
    def canonical_asset(self) -> str:
        """
        Internal asset identity used by the analysis pipeline.

        Pocket Option uses GBPUSD_otc as the API symbol, while the rest of
        the system must see one consistent market identity.
        """
        asset = self.asset.upper()

        if asset.endswith("_OTC"):
            return asset.replace("_OTC", "")

        return asset

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    @property
    def reconnect_count(self) -> int:
        return self._reconnect_count

    @property
    def last_message_at(self) -> Optional[float]:
        return self._last_message_at

    async def connect(self) -> None:
        """
        Connect, authenticate, wait for the platform asset list,
        then resolve GBPUSD OTC against the assets actually returned.
        """
        async with self._connect_lock:
            if self._connected and self._client is not None:
                return

            await self._shutdown_client()

            try:
                client = PocketOptionAsync(self._ssid)

                wait_result = client.wait_for_assets(timeout=60.0)
                if inspect.isawaitable(wait_result):
                    await wait_result

                self._client = client
                self._asset_symbol = await self._resolve_asset(client)
                self._connected = True
                self._last_error = None

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._connected = False
                self._last_error = f"{type(exc).__name__}: {exc}"
                await self._shutdown_client()
                raise PocketConnectionError(
                    f"Pocket Option connection failed: {self._last_error}"
                ) from exc

    async def close(self) -> None:
        self._connected = False
        await self._shutdown_client()

    async def stream_ticks(self) -> AsyncIterator[MarketTick]:
        """
        Infinite live market-data stream with automatic reconnection.

        This generator NEVER exits because of provider stream termination.
        It only stops on cancellation.
        """

        delay = max(
            0.25,
            float(CONFIG.STREAM_RECONNECT_DELAY_SECONDS),
        )

        max_delay = max(
            delay,
            float(CONFIG.STREAM_MAX_RECONNECT_DELAY_SECONDS),
        )

        reconnect_attempt = 0

        while True:
            try:
                if not self._connected or self._client is None:
                    await self.connect()

                if self._client is None:
                    raise PocketConnectionError(
                        "Pocket client unavailable."
                    )

                stream = await self._subscribe_with_fallback(
                    self._client
                )

                # Guard against providers returning an already-dead stream.
                if stream is None or not hasattr(stream, "__aiter__"):
                    raise PocketConnectionError(
                        "Pocket provider returned an invalid live stream."
                    )

                async for raw in stream:
                    tick = self._normalize_tick(
                        raw,
                        self.asset,
                    )

                    self._last_message_at = tick.received_at
                    self._last_error = None

                    reconnect_attempt = 0

                    yield tick

                reconnect_attempt += 1

                self._last_error = (
                    "Provider stream closed. "
                    f"Reconnect attempt={reconnect_attempt}"
                )

                self._connected = False

                await self._shutdown_client()

                await asyncio.sleep(
                    min(
                        delay * reconnect_attempt,
                        max_delay,
                    )
                )

                continue

            except asyncio.CancelledError:
                await self.close()
                raise

            except Exception as exc:
                reconnect_attempt += 1

                self._last_error = (
                    f"{type(exc).__name__}: {exc}"
                )

                self._reconnect_count += 1

                self._connected = False

                await self._shutdown_client()

                await asyncio.sleep(
                    min(
                        delay * reconnect_attempt,
                        max_delay,
                    )
                )

                continue

    async def fetch_historical_candles(
        self,
        timeframe_seconds: int = CONFIG.BASE_TIMEFRAME_SECONDS,
        count: int = CONFIG.MIN_BASE_CANDLES,
    ) -> list[HistoricalCandle]:
        """
        One-time historical backfill used for startup, memory and backtesting.

        This method is deliberately separate from the live stream so historical
        polling is never used as a fake real-time feed.
        """
        if timeframe_seconds <= 0:
            raise ValueError("timeframe_seconds must be greater than zero.")
        if count <= 0:
            raise ValueError("count must be greater than zero.")

        await self.connect()

        if self._client is None:
            raise PocketConnectionError("Pocket client was not initialized.")

        result = self._client.get_candles(
            self.history_asset,
            int(timeframe_seconds),
            int(count),
        )
        if inspect.isawaitable(result):
            result = await result

        if not isinstance(result, (list, tuple)):
            raise PocketDataError(
                f"Unexpected historical candle response: {type(result).__name__}"
            )

        candles: list[HistoricalCandle] = []
        for raw in result:
            try:
                candles.append(
                    self._normalize_historical_candle(
                        raw=raw,
                        asset=self.history_asset,
                        timeframe_seconds=int(timeframe_seconds),
                    )
                )
            except PocketDataError:
                # A malformed row is skipped; an entirely malformed response
                # still fails below.
                continue

        candles.sort(key=lambda candle: candle.timestamp)

        if not candles:
            raise PocketDataError("Pocket Option returned no valid historical candles.")

        return candles[-int(count):]

    async def fetch_recent_ticks(
        self,
        lookback_seconds: int,
    ) -> list[MarketTick]:
        """
        Fetch raw recent ticks when the installed library supports get_ticks().
        Useful for startup gap recovery and precise 30-second reconstruction.
        """
        if lookback_seconds <= 0:
            raise ValueError("lookback_seconds must be greater than zero.")

        await self.connect()

        if self._client is None:
            raise PocketConnectionError("Pocket client was not initialized.")

        getter = getattr(self._client, "get_ticks", None)
        if getter is None:
            raise PocketDataError(
                "Installed BinaryOptionsToolsV2 does not expose get_ticks()."
            )

        result = getter(self.asset, int(lookback_seconds))
        if inspect.isawaitable(result):
            result = await result

        if not isinstance(result, (list, tuple)):
            raise PocketDataError(
                f"Unexpected tick history response: {type(result).__name__}"
            )

        ticks: list[MarketTick] = []
        for raw in result:
            try:
                ticks.append(self._normalize_tick(raw, self.asset))
            except PocketDataError:
                continue

        ticks.sort(key=lambda tick: tick.timestamp)
        return ticks

    async def server_time(self) -> Optional[int]:
        """
        Return Pocket Option server time when available.
        Failure here never breaks the market-data pipeline.
        """
        try:
            await self.connect()
            if self._client is None:
                return None

            method = getattr(self._client, "get_server_time", None)
            if method is None:
                method = getattr(self._client, "server_time", None)
            if method is None:
                return None

            result = method()
            if inspect.isawaitable(result):
                result = await result

            return int(result) if result is not None else None
        except Exception:
            return None

    async def _subscribe_with_fallback(self, client: PocketOptionAsync) -> Any:
        """
        Try the resolved platform asset first, then configured aliases.

        This directly addresses the common OTC `Assets not found` issue without
        hardcoding a single spelling and without asking the user to alter code.
        """
        candidates: list[str] = []

        for candidate in (self._asset_symbol, *self._asset_candidates):
            if candidate and candidate not in candidates:
                candidates.append(candidate)

        errors: list[str] = []

        for candidate in candidates:
            try:
                stream = await client.subscribe_symbol(candidate)
                self._asset_symbol = candidate
                return stream
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                errors.append(f"{candidate}: {type(exc).__name__}: {exc}")

        joined = " | ".join(errors)
        raise PocketConnectionError(
            f"Could not subscribe to GBPUSD OTC. Tried: {joined}"
        )

    async def _resolve_asset(self, client: PocketOptionAsync) -> str:
        """
        Resolve the Pocket Option API symbol deterministically.

        `symbol` (for example `GBPUSD_otc`) is used for every API call.
        `name` / display label (for example `GBP/USD OTC`) is retained only
        for presentation and is never returned as the trading symbol.
        """
        fallback_symbol = self._asset_candidates[0]

        method = getattr(client, "active_assets", None)
        if method is None:
            self._asset_label = None
            return fallback_symbol

        try:
            result = method()
            if inspect.isawaitable(result):
                result = await result
        except Exception:
            self._asset_label = None
            return fallback_symbol

        records = self._extract_asset_records(result)
        if not records:
            self._asset_label = None
            return fallback_symbol

        candidate_keys = {
            self._normalize_asset_name(candidate): candidate
            for candidate in self._asset_candidates
        }

        # Prefer an explicit provider API symbol that matches our candidates.
        for symbol, label in records:
            if not symbol:
                continue
            symbol_key = self._normalize_asset_name(symbol)
            if symbol_key in candidate_keys:
                self._asset_label = label or symbol
                return self.normalize_asset(symbol)

        # Accept an explicit GBPUSD OTC symbol even if provider punctuation/case changes.
        for symbol, label in records:
            if not symbol:
                continue
            symbol_key = self._normalize_asset_name(symbol)
            if "gbpusd" in symbol_key and "otc" in symbol_key:
                self._asset_label = label or symbol
                return self.normalize_asset(symbol)

        # If only a display label is exposed, keep it for UI but return our
        # configured API symbol rather than the label.
        for _, label in records:
            if not label:
                continue
            label_key = self._normalize_asset_name(label)
            if label_key in candidate_keys or (
                "gbpusd" in label_key and "otc" in label_key
            ):
                self._asset_label = label
                return self.normalize_asset(fallback_symbol)

        self._asset_label = None
        return self.normalize_asset(fallback_symbol)

    async def _shutdown_client(self) -> None:
        client = self._client
        self._client = None
        self._connected = False

        if client is None:
            return

        try:
            result = client.shutdown()
            if inspect.isawaitable(result):
                await result
        except Exception:
            pass

    @staticmethod
    def _load_ssid() -> str:
        full_ssid = os.getenv("POCKET_SSID", "").strip()
        if full_ssid:
            return full_ssid

        session = os.getenv("POCKET_SESSION_ID", "").strip()

        # Allow an already-complete Socket.IO auth payload to live in the old
        # variable without forcing the user to change their .env.
        if session.startswith("42["):
            return session

        uid_raw = os.getenv("POCKET_USER_ID", "").strip()
        demo_raw = os.getenv("POCKET_IS_DEMO", "1").strip().lower()

        if not session:
            raise PocketConnectionError(
                "Missing POCKET_SESSION_ID (or POCKET_SSID) in .env."
            )
        if not uid_raw:
            raise PocketConnectionError(
                "Missing POCKET_USER_ID in .env."
            )

        demo = demo_raw in {"1", "true", "yes", "y", "on"}

        try:
            uid: Any = int(uid_raw)
        except ValueError:
            uid = uid_raw

        payload = {
            "session": session,
            "isDemo":  1,
            "uid": uid,
            "platform": 2,
            "isFastHistory": True,
            "isOptimized": True,
        }

        return '42["auth",' + json.dumps(
            payload,
            separators=(",", ":"),
            ensure_ascii=False,
        ) + "]"

    @classmethod
    def _extract_asset_records(
        cls,
        payload: Any,
    ) -> list[tuple[Optional[str], Optional[str]]]:
        """Extract `(api_symbol, display_label)` pairs without mixing them."""
        records: list[tuple[Optional[str], Optional[str]]] = []
        seen: set[tuple[Optional[str], Optional[str]]] = set()

        def add(symbol: Optional[str], label: Optional[str]) -> None:
            clean_symbol = (
                str(symbol).strip()
                if isinstance(symbol, str) and str(symbol).strip()
                else None
            )
            clean_label = (
                str(label).strip()
                if isinstance(label, str) and str(label).strip()
                else None
            )
            if clean_symbol is None and clean_label is None:
                return
            item = (clean_symbol, clean_label)
            if item not in seen:
                seen.add(item)
                records.append(item)

        def looks_like_symbol(value: str) -> bool:
            normalized = cls._normalize_asset_name(value)
            return "gbpusd" in normalized and "otc" in normalized

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                explicit_symbol = None
                for key in ("symbol", "asset", "ticker", "instrument"):
                    child = value.get(key)
                    if isinstance(child, str) and child.strip():
                        explicit_symbol = child.strip()
                        break

                label = None
                for key in ("name", "label", "display_name", "displayName"):
                    child = value.get(key)
                    if isinstance(child, str) and child.strip():
                        label = child.strip()
                        break

                if explicit_symbol is not None:
                    add(explicit_symbol, label)

                for key, child in value.items():
                    if (
                        isinstance(key, str)
                        and looks_like_symbol(key)
                        and isinstance(child, dict)
                    ):
                        child_label = child.get("name")
                        if not isinstance(child_label, str):
                            child_label = child.get("label")
                        add(key, child_label if isinstance(child_label, str) else None)

                    if isinstance(child, (dict, list, tuple, set)):
                        walk(child)

            elif isinstance(value, (list, tuple, set)):
                for child in value:
                    walk(child)

        walk(payload)
        return records

    @classmethod
    def normalize_asset(cls, name: str) -> str:
        """Return the canonical internal asset identity.

        Display labels from providers (for example ``GBP/USD OTC``) must never
        leak into the pipeline because candle validation depends on a single
        asset identity.
        """
        key = cls._normalize_asset_name(name)
        if "gbpusd" in key and "otc" in key:
            return CANONICAL_GBPUSD_ASSET
        return str(name).strip()

    @staticmethod
    def _normalize_asset_name(name: str) -> str:
        return "".join(ch for ch in str(name).lower() if ch.isalnum())

    @staticmethod
    def _canonical_from_asset(asset: str) -> str:
        """Convert provider symbols into one internal market identity."""
        value = str(asset).upper().strip()
        if value.endswith("_OTC"):
            value = value[:-4]
        return value

    @classmethod
    def _normalize_tick(cls, raw: Any, asset: str) -> MarketTick:
        received_at = time.time()
        timestamp: Any = None
        price: Any = None

        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                try:
                    price = float(raw)
                    timestamp = received_at
                except ValueError as exc:
                    raise PocketDataError(
                        "String market-data message is not valid JSON or price."
                    ) from exc

        if isinstance(raw, dict):
            timestamp = cls._first_present(
                raw,
                ("time", "timestamp", "ts", "datetime"),
                default=timestamp,
            )
            price = cls._first_present(
                raw,
                ("price", "close", "value", "last"),
                default=price,
            )

        elif isinstance(raw, (list, tuple)) and len(raw) >= 2:
            timestamp = raw[0]
            price = raw[1]

        elif isinstance(raw, (int, float)):
            timestamp = received_at
            price = raw

        else:
            if timestamp is None:
                timestamp = (
                    getattr(raw, "time", None)
                    or getattr(raw, "timestamp", None)
                    or getattr(raw, "ts", None)
                )
            if price is None:
                price = getattr(raw, "price", None)
                if price is None:
                    price = getattr(raw, "close", None)

        timestamp = cls._coerce_timestamp(timestamp, fallback=received_at)

        try:
            price = float(price)
        except (TypeError, ValueError) as exc:
            raise PocketDataError(
                f"Could not extract a valid price from {type(raw).__name__}."
            ) from exc

        if price <= 0:
            raise PocketDataError("Received a non-positive market price.")

        return MarketTick(
            timestamp=timestamp,
            price=price,
            asset=cls._canonical_from_asset(asset),
            received_at=received_at,
        )

    @classmethod
    def _normalize_historical_candle(
        cls,
        raw: Any,
        asset: str,
        timeframe_seconds: int,
    ) -> HistoricalCandle:
        if not isinstance(raw, dict):
            raw = {
                "time": getattr(raw, "time", None),
                "open": getattr(raw, "open", None),
                "high": getattr(raw, "high", None),
                "low": getattr(raw, "low", None),
                "close": getattr(raw, "close", None),
            }

        timestamp = cls._coerce_timestamp(
            cls._first_present(raw, ("time", "timestamp", "ts")),
            fallback=None,
        )

        try:
            open_ = float(raw["open"])
            high = float(raw["high"])
            low = float(raw["low"])
            close = float(raw["close"])
        except (KeyError, TypeError, ValueError) as exc:
            raise PocketDataError("Malformed historical OHLC candle.") from exc

        if timestamp is None:
            raise PocketDataError("Historical candle has no timestamp.")

        if min(open_, high, low, close) <= 0:
            raise PocketDataError("Historical candle contains non-positive price.")

        if high < max(open_, close, low) or low > min(open_, close, high):
            raise PocketDataError("Historical candle has inconsistent OHLC values.")

        return HistoricalCandle(
            timestamp=float(timestamp),
            open=open_,
            high=high,
            low=low,
            close=close,
            asset=cls._canonical_from_asset(asset),
            timeframe_seconds=int(timeframe_seconds),
        )

    @staticmethod
    def _first_present(
        mapping: dict[str, Any],
        keys: tuple[str, ...],
        default: Any = None,
    ) -> Any:
        for key in keys:
            if key in mapping and mapping[key] is not None:
                return mapping[key]
        return default

    @staticmethod
    def _coerce_timestamp(
        value: Any,
        fallback: Optional[float],
    ) -> Optional[float]:
        if value is None:
            return fallback

        if hasattr(value, "timestamp") and callable(value.timestamp):
            try:
                value = value.timestamp()
            except Exception:
                return fallback

        try:
            timestamp = float(value)
        except (TypeError, ValueError):
            return fallback

        # Normalize milliseconds/microseconds/nanoseconds to Unix seconds.
        while timestamp > 10_000_000_000:
            timestamp /= 1000.0

        if timestamp <= 0:
            return fallback

        return timestamp