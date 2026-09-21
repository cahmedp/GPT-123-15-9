from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Optional

from rich import box
from rich.align import Align
from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from config import CONFIG


class TerminalDashboard:
    """
    Rich terminal command center for the Personal AI Trading Analyst.

    The dashboard is presentation-only:
        - no market-data collection
        - no model decisions
        - no trade execution

    It receives snapshots produced by the orchestrator and renders them in one
    continuously refreshed terminal UI.
    """

    def __init__(
        self,
        console: Optional[Console] = None,
        *,
        refresh_per_second: Optional[float] = None,
        use_emoji: bool = True,
    ) -> None:
        self.console = console or Console()

        refresh_seconds = self._config_float(
            "UI_REFRESH_SECONDS",
            1.0,
        )

        if refresh_per_second is None:
            refresh_per_second = (
                1.0 / refresh_seconds
                if refresh_seconds > 0
                else 1.0
            )

        self.refresh_per_second = max(
            float(refresh_per_second),
            0.2,
        )

        self.use_emoji = bool(use_emoji)

        self._live: Optional[Live] = None
        self._last_renderable: Optional[
            RenderableType
        ] = None

    def start(self) -> None:
        if self._live is not None:
            return

        self._last_renderable = self._startup_renderable()

        self._live = Live(
            self._last_renderable,
            console=self.console,
            refresh_per_second=self.refresh_per_second,
            transient=False,
            screen=False,
            vertical_overflow="visible",
        )

        self._live.start()

    def stop(self) -> None:
        if self._live is None:
            return

        self._live.stop()
        self._live = None

    def update(
        self,
        *,
        session: Any = None,
        connector: Optional[Mapping[str, Any]] = None,
        market: Any = None,
        regime: Any = None,
        debate: Any = None,
        world: Any = None,
        simulation: Any = None,
        final_decision: Any = None,
        memory_summary: Any = None,
        learning_context: Optional[
            Mapping[str, Any]
        ] = None,
        goal_context: Optional[
            Mapping[str, Any]
        ] = None,
        status_message: Optional[str] = None,
    ) -> None:
        renderable = self.render(
            session=session,
            connector=connector,
            market=market,
            regime=regime,
            debate=debate,
            world=world,
            simulation=simulation,
            final_decision=final_decision,
            memory_summary=memory_summary,
            learning_context=learning_context,
            goal_context=goal_context,
            status_message=status_message,
        )

        self._last_renderable = renderable

        if self._live is None:
            self.console.print(
                renderable
            )
            return

        self._live.update(
            renderable,
            refresh=True,
        )

    def render(
        self,
        *,
        session: Any = None,
        connector: Optional[Mapping[str, Any]] = None,
        market: Any = None,
        regime: Any = None,
        debate: Any = None,
        world: Any = None,
        simulation: Any = None,
        final_decision: Any = None,
        memory_summary: Any = None,
        learning_context: Optional[
            Mapping[str, Any]
        ] = None,
        goal_context: Optional[
            Mapping[str, Any]
        ] = None,
        status_message: Optional[str] = None,
    ) -> Group:
        connector = connector or {}
        learning_context = (
            learning_context or {}
        )
        goal_context = (
            goal_context or {}
        )

        header = self._header(
            session=session,
            connector=connector,
            market=market,
            status_message=status_message,
        )

        market_panel = self._market_panel(
            market=market,
            regime=regime,
        )

        agent_panel = self._agent_panel(
            debate=debate,
        )

        simulation_panel = self._simulation_panel(
            world=world,
            simulation=simulation,
        )

        decision_panel = self._decision_panel(
            final_decision=final_decision,
        )

        memory_panel = self._memory_panel(
            memory_summary=memory_summary,
            learning_context=learning_context,
            goal_context=goal_context,
        )

        footer = self._footer()

        return Group(
            header,
            market_panel,
            agent_panel,
            simulation_panel,
            decision_panel,
            memory_panel,
            footer,
        )

    def show_error(
        self,
        message: str,
    ) -> None:
        text = Text()
        text.append(
            self._icon("❌ "),
            style="bold red",
        )
        text.append(
            "ERROR  ",
            style="bold red",
        )
        text.append(
            str(message),
            style="red",
        )

        self._publish(
            Panel(
                text,
                border_style="red",
                box=box.ROUNDED,
            )
        )

    def show_warning(
        self,
        message: str,
    ) -> None:
        text = Text()
        text.append(
            self._icon("⚠ "),
            style="bold yellow",
        )
        text.append(
            str(message),
            style="yellow",
        )

        self._publish(
            Panel(
                text,
                border_style="yellow",
                box=box.ROUNDED,
            )
        )

    def show_shutdown(
        self,
        reason: str = "Session finished.",
    ) -> None:
        self._publish(
            Panel(
                Align.center(
                    Text(
                        f"{self._icon('■ ')}{reason}",
                        style="bold cyan",
                    )
                ),
                border_style="cyan",
                box=box.ROUNDED,
            )
        )

    def _header(
        self,
        *,
        session: Any,
        connector: Mapping[str, Any],
        market: Any,
        status_message: Optional[str],
    ) -> Panel:
        title = Text()

        title.append(
            self._icon("◈ "),
            style="bold bright_cyan",
        )
        title.append(
            "PERSONAL AI TRADING ANALYST",
            style="bold bright_cyan",
        )
        title.append(
            "  |  ",
            style="dim",
        )
        title.append(
            str(
                getattr(
                    CONFIG,
                    "PAIR",
                    "GBPUSD_OTC",
                )
            ),
            style="bold bright_white",
        )

        subtitle = Text()

        mode = str(
            getattr(
                CONFIG,
                "SYSTEM_MODE",
                "CONSULTANT",
            )
        )

        subtitle.append(
            f"MODE: {mode}",
            style="bold green",
        )

        subtitle.append(
            "   •   ",
            style="dim",
        )

        connected = bool(
            connector.get(
                "connected",
                False,
            )
        )

        subtitle.append(
            "DATA: LIVE"
            if connected
            else "DATA: CONNECTING",
            style=(
                "bold green"
                if connected
                else "bold yellow"
            ),
        )

        asset = connector.get(
            "asset"
        )

        if asset:
            subtitle.append(
                f" ({asset})",
                style="dim",
            )

        price = self._safe_attr(
            market,
            "price",
            None,
        )

        if price is not None:
            subtitle.append(
                "   •   ",
                style="dim",
            )
            subtitle.append(
                f"PRICE: {self._fmt_price(price)}",
                style="bold white",
            )

        remaining = self._session_remaining(
            session
        )

        if remaining is not None:
            subtitle.append(
                "   •   ",
                style="dim",
            )
            subtitle.append(
                f"SESSION LEFT: {remaining}",
                style="cyan",
            )

        if status_message:
            subtitle.append(
                "\n"
            )
            subtitle.append(
                str(status_message),
                style="italic bright_black",
            )

        body = Group(
            Align.center(title),
            Align.center(subtitle),
        )

        return Panel(
            body,
            border_style="bright_cyan",
            box=box.DOUBLE,
            padding=(
                0,
                1,
            ),
        )

    def _market_panel(
        self,
        *,
        market: Any,
        regime: Any,
    ) -> Panel:
        table = Table(
            box=box.SIMPLE_HEAVY,
            expand=True,
            show_header=True,
            header_style="bold cyan",
        )

        table.add_column(
            "TF",
            justify="center",
            width=7,
        )
        table.add_column(
            "Bias",
            justify="center",
        )
        table.add_column(
            "Trend",
            justify="center",
        )
        table.add_column(
            "Noise",
            justify="center",
        )
        table.add_column(
            "Compression",
            justify="center",
        )
        table.add_column(
            "Expansion",
            justify="center",
        )
        table.add_column(
            "Structure",
            justify="center",
        )

        if market is None:
            table.add_row(
                "30s",
                "—",
                "—",
                "—",
                "—",
                "—",
                "WARMUP",
            )
            table.add_row(
                "1m",
                "—",
                "—",
                "—",
                "—",
                "—",
                "WARMUP",
            )
            table.add_row(
                "5m",
                "—",
                "—",
                "—",
                "—",
                "—",
                "WARMUP",
            )
        else:
            for label, attribute in (
                (
                    "30s",
                    "base_30s",
                ),
                (
                    "1m",
                    "setup_1m",
                ),
                (
                    "5m",
                    "context_5m",
                ),
            ):
                timeframe = getattr(
                    market,
                    attribute,
                    None,
                )

                table.add_row(
                    label,
                    self._styled_bias(
                        self._timeframe_bias(
                            timeframe
                        )
                    ),
                    self._percent(
                        self._timeframe_trend(
                            timeframe
                        )
                    ),
                    self._percent(
                        self._safe_attr(
                            timeframe,
                            "noise_score",
                            0.0,
                        )
                    ),
                    self._percent(
                        self._safe_attr(
                            timeframe,
                            "compression_score",
                            0.0,
                        )
                    ),
                    self._percent(
                        self._safe_attr(
                            timeframe,
                            "expansion_score",
                            0.0,
                        )
                    ),
                    self._structure_text(
                        timeframe
                    ),
                )

        regime_name = self._safe_attr(
            regime,
            "primary_regime",
            "WARMUP",
        )

        regime_confidence = self._safe_attr(
            regime,
            "regime_confidence",
            0.0,
        )

        readiness = self._safe_attr(
            market,
            "readiness_state",
            "WARMUP",
        )

        footer = Text()

        footer.append(
            f"Regime: {regime_name}",
            style=self._regime_style(
                str(regime_name)
            ),
        )
        footer.append(
            "   •   ",
            style="dim",
        )
        footer.append(
            f"Regime confidence: "
            f"{self._percent(regime_confidence)}",
        )
        footer.append(
            "   •   ",
            style="dim",
        )
        footer.append(
            f"Readiness: {readiness}",
            style=self._readiness_style(
                str(readiness)
            ),
        )

        return Panel(
            Group(
                table,
                Align.center(
                    footer
                ),
            ),
            title=(
                f"{self._icon('📊 ')}"
                "MARKET INTELLIGENCE"
            ),
            border_style="blue",
            box=box.ROUNDED,
        )

    def _agent_panel(
        self,
        *,
        debate: Any,
    ) -> Panel:
        table = Table(
            box=box.SIMPLE,
            expand=True,
            show_header=True,
            header_style="bold magenta",
        )

        table.add_column(
            "Agent",
            ratio=2,
        )
        table.add_column(
            "View",
            justify="center",
        )
        table.add_column(
            "Score",
            justify="right",
        )
        table.add_column(
            "Confidence",
            justify="right",
        )
        table.add_column(
            "Uncertainty",
            justify="right",
        )
        table.add_column(
            "Veto",
            justify="center",
        )

        opinions = (
            getattr(
                debate,
                "opinions",
                (),
            )
            if debate is not None
            else ()
        )

        if not opinions:
            table.add_row(
                "Waiting",
                "WAIT",
                "0.00",
                "0%",
                "100%",
                "—",
            )
        else:
            for opinion in opinions:
                direction = str(
                    self._safe_attr(
                        opinion,
                        "direction",
                        "WAIT",
                    )
                )

                table.add_row(
                    str(
                        self._safe_attr(
                            opinion,
                            "agent",
                            "agent",
                        )
                    ),
                    self._styled_direction(
                        direction
                    ),
                    f"{self._safe_float(self._safe_attr(opinion, 'score', 0.0)):+.2f}",
                    self._percent(
                        self._safe_attr(
                            opinion,
                            "confidence",
                            0.0,
                        )
                    ),
                    self._percent(
                        self._safe_attr(
                            opinion,
                            "uncertainty",
                            1.0,
                        )
                    ),
                    (
                        "[bold red]YES[/bold red]"
                        if bool(
                            self._safe_attr(
                                opinion,
                                "veto",
                                False,
                            )
                        )
                        else "[green]NO[/green]"
                    ),
                )

        consensus = self._safe_attr(
            debate,
            "consensus_direction",
            "WAIT",
        )

        confidence = self._safe_attr(
            debate,
            "consensus_confidence",
            0.0,
        )

        disagreement = self._safe_attr(
            debate,
            "disagreement_score",
            1.0,
        )

        summary = Text.from_markup(
            (
                f"Consensus: "
                f"{self._styled_direction(str(consensus))}"
                f"   •   Confidence: "
                f"{self._percent(confidence)}"
                f"   •   Disagreement: "
                f"{self._percent(disagreement)}"
            )
        )

        return Panel(
            Group(
                table,
                Align.center(
                    summary
                ),
            ),
            title=(
                f"{self._icon('🧠 ')}"
                "MULTI-AGENT BRAIN"
            ),
            border_style="magenta",
            box=box.ROUNDED,
        )

    def _simulation_panel(
        self,
        *,
        world: Any,
        simulation: Any,
    ) -> Panel:
        table = Table(
            box=None,
            expand=True,
            show_header=False,
        )

        table.add_column(
            "Metric",
            style="bold",
        )
        table.add_column(
            "Value",
            justify="right",
        )
        table.add_column(
            "Metric",
            style="bold",
        )
        table.add_column(
            "Value",
            justify="right",
        )

        world_quality = self._safe_attr(
            world,
            "evidence_quality",
            0.0,
        )

        memory_cases = self._safe_attr(
            world,
            "memory_cases_used",
            0,
        )

        bullish = self._safe_attr(
            simulation,
            "bullish_probability",
            0.0,
        )

        bearish = self._safe_attr(
            simulation,
            "bearish_probability",
            0.0,
        )

        sideways = self._safe_attr(
            simulation,
            "sideways_probability",
            0.0,
        )

        failure = self._safe_attr(
            simulation,
            "failure_probability",
            1.0,
        )

        sim_conf = self._safe_attr(
            simulation,
            "simulation_confidence",
            0.0,
        )

        dominant = self._safe_attr(
            simulation,
            "dominant_scenario",
            "WAIT",
        )

        table.add_row(
            "World quality",
            self._percent(
                world_quality
            ),
            "Historical cases",
            str(memory_cases),
        )

        table.add_row(
            "Bullish",
            f"[green]{self._percent(bullish)}[/green]",
            "Bearish",
            f"[red]{self._percent(bearish)}[/red]",
        )

        table.add_row(
            "Sideways",
            f"[yellow]{self._percent(sideways)}[/yellow]",
            "Failure",
            f"[bright_red]{self._percent(failure)}[/bright_red]",
        )

        table.add_row(
            "Simulation confidence",
            self._percent(
                sim_conf
            ),
            "Dominant scenario",
            str(dominant),
        )

        return Panel(
            table,
            title=(
                f"{self._icon('🔮 ')}"
                "WORLD MODEL & SCENARIOS"
            ),
            border_style="bright_blue",
            box=box.ROUNDED,
        )

    def _decision_panel(
        self,
        *,
        final_decision: Any,
    ) -> Panel:
        if final_decision is None:
            action = "WAIT"
            confidence = 0.0
            required = self._config_float(
                "MIN_ADVISORY_CONFIDENCE",
                0.68,
            )
            risk = 1.0
            strength = "NONE"
            blocked = True
            block_reasons = (
                "waiting for sufficient market data",
            )
        else:
            action = str(
                self._safe_attr(
                    final_decision,
                    "advisory_action",
                    "WAIT",
                )
            ).upper()

            confidence = self._safe_attr(
                final_decision,
                "calibrated_confidence",
                0.0,
            )

            required = self._safe_attr(
                final_decision,
                "required_confidence",
                self._config_float(
                    "MIN_ADVISORY_CONFIDENCE",
                    0.68,
                ),
            )

            risk = self._safe_attr(
                final_decision,
                "risk_score",
                1.0,
            )

            strength = str(
                self._safe_attr(
                    final_decision,
                    "signal_strength",
                    "NONE",
                )
            )

            blocked = bool(
                self._safe_attr(
                    final_decision,
                    "blocked",
                    True,
                )
            )

            block_reasons = tuple(
                self._safe_attr(
                    final_decision,
                    "block_reasons",
                    (),
                )
                or ()
            )

        action_text = Text()

        if action == "BUY":
            action_text.append(
                self._icon("▲ "),
                style="bold bright_green",
            )
            action_text.append(
                "BUY",
                style="bold bright_green",
            )
        elif action == "SELL":
            action_text.append(
                self._icon("▼ "),
                style="bold bright_red",
            )
            action_text.append(
                "SELL",
                style="bold bright_red",
            )
        else:
            action_text.append(
                self._icon("◆ "),
                style="bold yellow",
            )
            action_text.append(
                "WAIT",
                style="bold yellow",
            )

        action_text.append(
            "   ",
        )
        action_text.append(
            f"Confidence {self._percent(confidence)}",
            style="bold white",
        )
        action_text.append(
            "   •   ",
            style="dim",
        )
        action_text.append(
            f"Required {self._percent(required)}",
            style="cyan",
        )
        action_text.append(
            "   •   ",
            style="dim",
        )
        action_text.append(
            f"Risk {self._percent(risk)}",
            style=self._risk_style(
                self._safe_float(
                    risk
                )
            ),
        )
        action_text.append(
            "   •   ",
            style="dim",
        )
        action_text.append(
            f"Strength {strength}",
            style="bold",
        )

        detail = Text()

        if blocked and block_reasons:
            detail.append(
                "Blocked: ",
                style="bold red",
            )
            detail.append(
                "; ".join(
                    str(reason)
                    for reason
                    in block_reasons[:4]
                ),
                style="red",
            )
        elif action in {
            "BUY",
            "SELL",
        }:
            detail.append(
                "All final safety gates passed.",
                style="green",
            )
        else:
            detail.append(
                "No directional recommendation yet.",
                style="yellow",
            )

        border_style = {
            "BUY": "bright_green",
            "SELL": "bright_red",
            "WAIT": "yellow",
        }.get(
            action,
            "yellow",
        )

        return Panel(
            Group(
                Align.center(
                    action_text
                ),
                Align.center(
                    detail
                ),
            ),
            title=(
                f"{self._icon('🎯 ')}"
                "FINAL ADVISORY"
            ),
            subtitle=(
                "Human decision required • No automatic execution"
            ),
            border_style=border_style,
            box=box.DOUBLE,
            padding=(
                1,
                1,
            ),
        )

    def _memory_panel(
        self,
        *,
        memory_summary: Any,
        learning_context: Mapping[str, Any],
        goal_context: Mapping[str, Any],
    ) -> Panel:
        table = Table(
            box=None,
            expand=True,
            show_header=False,
        )

        table.add_column(
            "A",
            style="bold",
        )
        table.add_column(
            "B",
            justify="right",
        )
        table.add_column(
            "C",
            style="bold",
        )
        table.add_column(
            "D",
            justify="right",
        )

        total_cases = self._safe_attr(
            memory_summary,
            "total_cases",
            0,
        )

        resolved_cases = self._safe_attr(
            memory_summary,
            "resolved_cases",
            0,
        )

        positive = self._safe_attr(
            memory_summary,
            "positive_outcomes",
            0,
        )

        negative = self._safe_attr(
            memory_summary,
            "negative_outcomes",
            0,
        )

        defensive = bool(
            learning_context.get(
                "defensive_mode",
                False,
            )
        )

        consecutive_bad = self._safe_int(
            learning_context.get(
                "consecutive_bad_outcomes",
                0,
            )
        )

        active_goals = self._safe_int(
            goal_context.get(
                "active_goal_count",
                0,
            )
        )

        table.add_row(
            "Memory cases",
            str(total_cases),
            "Resolved",
            str(resolved_cases),
        )

        table.add_row(
            "Positive",
            f"[green]{positive}[/green]",
            "Negative",
            f"[red]{negative}[/red]",
        )

        table.add_row(
            "Defensive mode",
            (
                "[bold red]ON[/bold red]"
                if defensive
                else "[green]OFF[/green]"
            ),
            "Bad streak",
            str(consecutive_bad),
        )

        table.add_row(
            "Active learning goals",
            str(active_goals),
            "Learning",
            (
                "[green]ENABLED[/green]"
                if bool(
                    getattr(
                        CONFIG,
                        "LEARNING_ENABLED",
                        True,
                    )
                )
                else "[yellow]DISABLED[/yellow]"
            ),
        )

        return Panel(
            table,
            title=(
                f"{self._icon('💾 ')}"
                "MEMORY & LEARNING"
            ),
            border_style="cyan",
            box=box.ROUNDED,
        )

    def _footer(
        self,
    ) -> Panel:
        now = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        text = Text()

        text.append(
            "Updated ",
            style="dim",
        )
        text.append(
            now,
            style="cyan",
        )
        text.append(
            "   •   ",
            style="dim",
        )
        text.append(
            "Ctrl+C to stop",
            style="bold white",
        )
        text.append(
            "   •   ",
            style="dim",
        )
        text.append(
            "Advisory system only",
            style="bold yellow",
        )

        return Panel(
            Align.center(
                text
            ),
            border_style="bright_black",
            box=box.SIMPLE,
            padding=(
                0,
                1,
            ),
        )

    def _startup_renderable(
        self,
    ) -> Panel:
        text = Text()

        text.append(
            self._icon("◈ "),
            style="bright_cyan",
        )

        text.append(
            "Starting Personal AI Trading Analyst...\n",
            style="bold bright_cyan",
        )

        text.append(
            "Waiting for Pocket Option data and warmup candles.",
            style="yellow",
        )

        return Panel(
            Align.center(
                text
            ),
            border_style="bright_cyan",
            box=box.DOUBLE,
        )

    def _publish(
        self,
        renderable: RenderableType,
    ) -> None:
        self._last_renderable = renderable

        if self._live is not None:
            self._live.update(
                renderable,
                refresh=True,
            )
        else:
            self.console.print(
                renderable
            )

    def _timeframe_bias(
        self,
        timeframe: Any,
    ) -> float:
        if timeframe is None:
            return 0.0

        for name in (
            "directional_bias",
            "bias",
            "trend_bias",
        ):
            value = getattr(
                timeframe,
                name,
                None,
            )

            if value is not None:
                return self._safe_float(
                    value
                )

        technical = getattr(
            timeframe,
            "technical",
            None,
        )

        if technical is not None:
            ema_fast = self._safe_float(
                getattr(
                    technical,
                    "ema_fast",
                    0.0,
                )
            )

            ema_slow = self._safe_float(
                getattr(
                    technical,
                    "ema_slow",
                    0.0,
                )
            )

            if ema_fast > ema_slow:
                return 0.5

            if ema_fast < ema_slow:
                return -0.5

        return 0.0

    def _timeframe_trend(
        self,
        timeframe: Any,
    ) -> float:
        if timeframe is None:
            return 0.0

        for name in (
            "trend_quality",
            "trend_strength",
            "directional_strength",
        ):
            value = getattr(
                timeframe,
                name,
                None,
            )

            if value is not None:
                return self._clip01(
                    value
                )

        return 0.0

    def _structure_text(
        self,
        timeframe: Any,
    ) -> str:
        if timeframe is None:
            return "—"

        structure = getattr(
            timeframe,
            "structure",
            None,
        )

        if structure is None:
            return "—"

        value = getattr(
            structure,
            "structure_state",
            "UNKNOWN",
        )

        return str(value)

    @staticmethod
    def _safe_attr(
        obj: Any,
        name: str,
        default: Any,
    ) -> Any:
        if obj is None:
            return default

        if isinstance(
            obj,
            Mapping,
        ):
            return obj.get(
                name,
                default,
            )

        return getattr(
            obj,
            name,
            default,
        )

    @staticmethod
    def _safe_float(
        value: Any,
        default: float = 0.0,
    ) -> float:
        try:
            number = float(
                value
            )
        except (
            TypeError,
            ValueError,
        ):
            return float(default)

        if number != number:
            return float(default)

        if number in {
            float("inf"),
            float("-inf"),
        }:
            return float(default)

        return number

    @staticmethod
    def _safe_int(
        value: Any,
        default: int = 0,
    ) -> int:
        try:
            return int(value)
        except (
            TypeError,
            ValueError,
        ):
            return int(default)

    @classmethod
    def _percent(
        cls,
        value: Any,
    ) -> str:
        return (
            f"{100.0 * cls._clip01(value):.0f}%"
        )

    @staticmethod
    def _fmt_price(
        value: Any,
    ) -> str:
        try:
            price = float(
                value
            )
        except (
            TypeError,
            ValueError,
        ):
            return "—"

        if price >= 100:
            return f"{price:.2f}"

        return f"{price:.5f}"

    @classmethod
    def _styled_bias(
        cls,
        value: Any,
    ) -> str:
        bias = cls._safe_float(
            value
        )

        if bias >= 0.15:
            return (
                f"[bold green]BULL "
                f"{bias:+.2f}[/bold green]"
            )

        if bias <= -0.15:
            return (
                f"[bold red]BEAR "
                f"{bias:+.2f}[/bold red]"
            )

        return (
            f"[yellow]NEUTRAL "
            f"{bias:+.2f}[/yellow]"
        )

    @staticmethod
    def _styled_direction(
        direction: str,
    ) -> str:
        direction = str(
            direction
        ).upper()

        if direction in {
            "BULLISH",
            "BUY",
        }:
            return (
                f"[bold green]{direction}"
                f"[/bold green]"
            )

        if direction in {
            "BEARISH",
            "SELL",
        }:
            return (
                f"[bold red]{direction}"
                f"[/bold red]"
            )

        return (
            f"[bold yellow]{direction}"
            f"[/bold yellow]"
        )

    @staticmethod
    def _regime_style(
        regime: str,
    ) -> str:
        regime = regime.upper()

        if "BULLISH" in regime:
            return "bold green"

        if "BEARISH" in regime:
            return "bold red"

        if "NOISE" in regime:
            return "bold bright_red"

        if "TRANSITION" in regime:
            return "bold yellow"

        if "COMPRESSION" in regime:
            return "bold cyan"

        return "bold white"

    @staticmethod
    def _readiness_style(
        readiness: str,
    ) -> str:
        readiness = readiness.upper()

        if readiness == "READY":
            return "bold green"

        if readiness in {
            "BLOCKED_NOISE",
            "WARMUP",
        }:
            return "bold red"

        return "bold yellow"

    @staticmethod
    def _risk_style(
        risk: float,
    ) -> str:
        if risk <= 0.30:
            return "bold green"

        if risk <= 0.60:
            return "bold yellow"

        return "bold red"

    @staticmethod
    def _session_remaining(
        session: Any,
    ) -> Optional[str]:
        if session is None:
            return None

        for name in (
            "remaining_seconds",
            "seconds_remaining",
        ):
            value = getattr(
                session,
                name,
                None,
            )

            if value is None:
                continue

            try:
                seconds = max(
                    int(
                        float(value)
                    ),
                    0,
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            hours, remainder = divmod(
                seconds,
                3600,
            )

            minutes, seconds = divmod(
                remainder,
                60,
            )

            return (
                f"{hours:02d}:"
                f"{minutes:02d}:"
                f"{seconds:02d}"
            )

        return None

    def _icon(
        self,
        text: str,
    ) -> str:
        if self.use_emoji:
            return text

        # Strip the leading glyph while preserving optional spacing.
        return ""

    @staticmethod
    def _config_float(
        name: str,
        default: float,
    ) -> float:
        try:
            return float(
                getattr(
                    CONFIG,
                    name,
                    default,
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            return float(default)

    @classmethod
    def _clip01(
        cls,
        value: Any,
    ) -> float:
        return min(
            max(
                cls._safe_float(
                    value
                ),
                0.0,
            ),
            1.0,
        )

    def __enter__(
        self,
    ) -> "TerminalDashboard":
        self.start()
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc: Any,
        traceback: Any,
    ) -> None:
        self.stop()
