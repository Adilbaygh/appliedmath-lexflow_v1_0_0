"""Tk desktop interface for the deterministic AppliedMath benchmark project."""

from __future__ import annotations

import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import traceback
from typing import Callable, TypeVar

import networkx as nx
import numpy as np

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext, ttk
except ImportError as exc:  # pragma: no cover - depends on the Python distribution
    raise RuntimeError(
        "Tkinter is not available. Install the standard Python distribution with Tcl/Tk support."
    ) from exc

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from .desktop_backend import (
    BenchmarkSnapshot,
    benchmark_description_uz,
    export_snapshot,
    find_project_root,
    generate_article_results,
    fraction_string,
    period_series,
    ratio_rows,
    resource_label_uz,
    result_files,
    run_tests,
    save_benchmark_result,
    solve_benchmark_at_path,
    stage_rows,
    users_with_activity,
    verification_rows,
)
from .operators import build_graph

T = TypeVar("T")


class MetricCard(ttk.Frame):
    def __init__(self, parent: tk.Misc, title: str, *, width: int = 22) -> None:
        super().__init__(parent, padding=(12, 8), style="Card.TFrame", width=width)
        self.grid_propagate(False)
        ttk.Label(self, text=title, style="CardTitle.TLabel").pack(anchor="w")
        self.value_var = tk.StringVar(value="—")
        ttk.Label(self, textvariable=self.value_var, style="CardValue.TLabel").pack(
            anchor="w", pady=(3, 0)
        )

    def set(self, value: str) -> None:
        self.value_var.set(value)


class LexFlowDesktopApp:
    """Main desktop window.  All solver work is delegated to the shared backend."""

    def __init__(self, root: tk.Tk, project_root: Path) -> None:
        self.root = root
        self.project_root = find_project_root(project_root)
        self.snapshot: BenchmarkSnapshot | None = None
        self._current_benchmark_path: Path | None = None
        self._busy = False
        self._task_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self._buttons: list[ttk.Button] = []

        self.root.title("AppliedMath — детерминистик лексикографик оқим модели")
        self.root.geometry("1320x840")
        self.root.minsize(1080, 700)
        self._center_window()
        self._configure_style()
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)
        self.root.report_callback_exception = self._report_callback_exception
        self.root.bind("<F5>", lambda _event: self.run_selected_benchmark())
        self.root.bind("<Control-g>", lambda _event: self.save_current_benchmark_result())
        self.root.bind("<Control-G>", lambda _event: self.save_current_benchmark_result())
        self.root.bind("<Control-Shift-G>", lambda _event: self.generate_article_outputs())

        self.status_var = tk.StringVar(value="Тайёр")
        self.benchmark_name_var = tk.StringVar(value="тармоқ танланмади")
        self.user_var = tk.StringVar()
        self.description_var = tk.StringVar(
            value="Файл > Тармоқ очиш орқали Data/benchmarks папкасидаги .json файлни танланг."
        )

        self._build_menu()
        self._build_header()
        self._build_controls()
        self._build_notebook()
        self._build_statusbar()
        self._refresh_result_files()

        self._log(f"Лойиҳа папкаси: {self.project_root}")
        self._log("Модель чегараси: фақат детерминистик rooted-tree benchmark’лар.")

    def _center_window(self) -> None:
        self.root.update_idletasks()
        width = 1320
        height = 840
        x = max(0, (self.root.winfo_screenwidth() - width) // 2)
        y = max(0, (self.root.winfo_screenheight() - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        available = style.theme_names()
        if sys.platform.startswith("win") and "vista" in available:
            style.theme_use("vista")
        elif "clam" in available:
            style.theme_use("clam")

        style.configure("Title.TLabel", font=("Segoe UI Semibold", 18))
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10))
        style.configure("Section.TLabel", font=("Segoe UI Semibold", 11))
        style.configure("Card.TFrame", relief="solid", borderwidth=1)
        style.configure("CardTitle.TLabel", font=("Segoe UI", 9))
        style.configure("CardValue.TLabel", font=("Segoe UI Semibold", 14))
        style.configure("Treeview", rowheight=25, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 9))
        style.configure("TNotebook.Tab", padding=(12, 7))

    def _build_menu(self) -> None:
        menu = tk.Menu(self.root)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="Тармоқ очиш", command=self.open_benchmark_file)
        file_menu.add_separator()
        file_menu.add_command(label="Тармоқни қайта ечиш (F5)", command=self.run_selected_benchmark)
        file_menu.add_command(label="Натижани сақлаш… (Ctrl+G)", command=self.save_current_benchmark_result)
        file_menu.add_separator()
        # Everything below is independent of whatever benchmark (if any) is
        # currently open in the GUI — it works even with nothing loaded.
        file_menu.add_command(
            label="Барча Data/benchmarks натижаларини қайта ҳисоблаш (Ctrl+Shift+G)",
            command=self.generate_article_outputs,
        )
        file_menu.add_command(label="Автоматик тестларни ишга тушириш", command=self.run_test_suite)
        file_menu.add_separator()
        file_menu.add_command(label="Натижалар папкасини очиш", command=lambda: self._open_path(self.project_root / "results"))
        file_menu.add_command(label="Лойиҳа папкасини очиш", command=lambda: self._open_path(self.project_root))
        file_menu.add_separator()
        file_menu.add_command(label="Чиқиш", command=self.root.destroy)
        menu.add_cascade(label="Файл", menu=file_menu)

        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(label="Модель чегараси", command=self._show_boundary)
        help_menu.add_command(label="Дастур ҳақида", command=self._show_about)
        menu.add_cascade(label="Ёрдам", menu=help_menu)
        self.root.configure(menu=menu)

    def _build_header(self) -> None:
        frame = ttk.Frame(self.root, padding=(18, 14, 18, 8))
        frame.pack(fill="x")
        ttk.Label(
            frame,
            text="AppliedMath: уч босқичли детерминистик лексикографик оқим модели",
            style="Title.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            frame,
            text=(
                "1-босқичнинг ёпиқ ечими, граф оператори — тугун баланси "
                "эквивалентлиги ва 1-, 2- ва 3-босқичларнинг сонли верификацияси"
            ),
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(3, 0))

    def _button(self, parent: tk.Misc, text: str, command: Callable[[], None]) -> ttk.Button:
        button = ttk.Button(parent, text=text, command=command)
        self._buttons.append(button)
        return button

    def _build_controls(self) -> None:
        controls = ttk.Frame(self.root, padding=(18, 6, 18, 10))
        controls.pack(fill="x")
        ttk.Label(controls, text="Назорат мисоли:", style="Section.TLabel").pack(side="left")
        self._button(controls, "Очиш…", self.open_benchmark_file).pack(side="left", padx=(8, 8))
        ttk.Label(
            controls, textvariable=self.benchmark_name_var, style="Section.TLabel"
        ).pack(side="left", padx=(0, 12))

        self._button(controls, "Ечиш", self.run_selected_benchmark).pack(side="left", padx=4)
        self._button(controls, "Натижани сақлаш…", self.save_current_benchmark_result).pack(side="left", padx=4)
        self._button(controls, "Барчасини қайта ҳисоблаш", self.generate_article_outputs).pack(side="left", padx=4)
        self._button(controls, "Тестлар", self.run_test_suite).pack(side="left", padx=4)
        self._button(controls, "CSV/Excel экспорт", self.export_current).pack(side="left", padx=4)
        self._button(controls, "Натижалар папкаси", lambda: self._open_path(self.project_root / "results")).pack(side="right", padx=4)

        self.progress = ttk.Progressbar(controls, mode="indeterminate", length=150)
        self.progress.pack(side="right", padx=(8, 12))

    def _build_notebook(self) -> None:
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=18, pady=(0, 10))
        self._build_overview_tab()
        self._build_allocations_tab()
        self._build_verification_tab()
        self._build_network_tab()
        self._build_files_tab()
        self._build_log_tab()

    def _build_overview_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text="Умумий натижа")

        description_box = ttk.LabelFrame(tab, text="Назорат мисоли тавсифи", padding=10)
        description_box.pack(fill="x")
        ttk.Label(
            description_box,
            textvariable=self.description_var,
            wraplength=1180,
            justify="left",
        ).pack(anchor="w")

        cards = ttk.Frame(tab, padding=(0, 12))
        cards.pack(fill="x")
        for column in range(5):
            cards.columnconfigure(column, weight=1, uniform="cards")
        self.card_closed = MetricCard(cards, "Ёпиқ λ*")
        self.card_lp = MetricCard(cards, "LP λ*")
        self.card_theta = MetricCard(cards, "2-босқич қониқиш")
        self.card_omega = MetricCard(cards, "3-босқич вариация")
        self.card_status = MetricCard(cards, "Верификация")
        for index, card in enumerate(
            (self.card_closed, self.card_lp, self.card_theta, self.card_omega, self.card_status)
        ):
            card.grid(row=0, column=index, sticky="nsew", padx=5)

        stage_box = ttk.LabelFrame(tab, text="Лексикографик босқичлар", padding=8)
        stage_box.pack(fill="both", expand=True)
        columns = ("stage", "min", "satisfaction", "variation", "status")
        self.stage_tree = ttk.Treeview(stage_box, columns=columns, show="headings", height=8)
        headings = {
            "stage": "Босқич",
            "min": "Минимал нисбат",
            "satisfaction": "Вазнланган қониқиш",
            "variation": "Вақт вариацияси",
            "status": "Solver ҳолати",
        }
        widths = {"stage": 150, "min": 170, "satisfaction": 210, "variation": 190, "status": 140}
        for column in columns:
            self.stage_tree.heading(column, text=headings[column])
            self.stage_tree.column(column, width=widths[column], anchor="center")
        self.stage_tree.pack(fill="both", expand=True)

        self.active_resource_var = tk.StringVar(value="Фаол ресурслар: —")
        ttk.Label(tab, textvariable=self.active_resource_var, padding=(3, 8, 3, 0)).pack(anchor="w")

    def _build_allocations_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Тақсимотлар")
        paned = ttk.Panedwindow(tab, orient="horizontal")
        paned.pack(fill="both", expand=True)

        table_frame = ttk.LabelFrame(paned, text="Фаол давр–истеъмолчи ёзувлари", padding=6)
        chart_frame = ttk.LabelFrame(paned, text="1-, 2- ва 3-босқич профили", padding=6)
        paned.add(table_frame, weight=3)
        paned.add(chart_frame, weight=2)

        columns = ("period", "user", "demand", "s1", "s2", "s3")
        self.ratio_tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        headings = {
            "period": "Давр",
            "user": "Истеъмолчи",
            "demand": "Талаб",
            "s1": "1-босқич",
            "s2": "2-босқич",
            "s3": "3-босқич",
        }
        widths = {"period": 90, "user": 120, "demand": 100, "s1": 105, "s2": 105, "s3": 105}
        for column in columns:
            self.ratio_tree.heading(column, text=headings[column])
            self.ratio_tree.column(column, width=widths[column], anchor="center")
        ratio_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.ratio_tree.yview)
        self.ratio_tree.configure(yscrollcommand=ratio_scroll.set)
        self.ratio_tree.pack(side="left", fill="both", expand=True)
        ratio_scroll.pack(side="right", fill="y")

        user_controls = ttk.Frame(chart_frame)
        user_controls.pack(fill="x", pady=(0, 6))
        ttk.Label(user_controls, text="Истеъмолчи:").pack(side="left")
        self.user_combo = ttk.Combobox(
            user_controls,
            textvariable=self.user_var,
            state="readonly",
            width=24,
        )
        self.user_combo.pack(side="left", padx=8)
        self.user_combo.bind("<<ComboboxSelected>>", lambda _event: self._draw_allocation_chart())

        self.allocation_figure = Figure(figsize=(6.0, 4.5), dpi=100, constrained_layout=True)
        self.allocation_ax = self.allocation_figure.add_subplot(111)
        self.allocation_canvas = FigureCanvasTkAgg(self.allocation_figure, master=chart_frame)
        self.allocation_canvas.get_tk_widget().pack(fill="both", expand=True)
        toolbar = NavigationToolbar2Tk(self.allocation_canvas, chart_frame, pack_toolbar=False)
        toolbar.update()
        toolbar.pack(fill="x")

    def _build_verification_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Верификация")
        columns = ("check", "value", "criterion", "status")
        self.verify_tree = ttk.Treeview(tab, columns=columns, show="headings")
        headings = {
            "check": "Текширув",
            "value": "Ҳисобланган қиймат",
            "criterion": "Қабул мезони",
            "status": "Натижа",
        }
        widths = {"check": 360, "value": 220, "criterion": 300, "status": 100}
        for column in columns:
            self.verify_tree.heading(column, text=headings[column])
            self.verify_tree.column(column, width=widths[column], anchor="w" if column == "check" else "center")
        self.verify_tree.tag_configure("pass", foreground="#176b36")
        self.verify_tree.tag_configure("fail", foreground="#a11d1d")
        self.verify_tree.pack(fill="both", expand=True)

        detail_frame = ttk.LabelFrame(tab, text="Математик маълумот", padding=8)
        detail_frame.pack(fill="x", pady=(10, 0))
        self.verification_detail_var = tk.StringVar(value="—")
        ttk.Label(detail_frame, textvariable=self.verification_detail_var, wraplength=1180, justify="left").pack(anchor="w")

    def _build_network_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(tab, text="Тармоқ")
        self.network_figure = Figure(figsize=(9.0, 5.2), dpi=100, constrained_layout=True)
        self.network_ax = self.network_figure.add_subplot(111)
        self.network_canvas = FigureCanvasTkAgg(self.network_figure, master=tab)
        self.network_canvas.get_tk_widget().pack(fill="both", expand=True)
        toolbar = NavigationToolbar2Tk(self.network_canvas, tab, pack_toolbar=False)
        toolbar.update()
        toolbar.pack(fill="x")

    def _build_files_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Натижа файллари")
        controls = ttk.Frame(tab)
        controls.pack(fill="x", pady=(0, 8))
        ttk.Button(controls, text="Янгилаш", command=self._refresh_result_files).pack(side="left")
        ttk.Button(controls, text="Танланган файлни очиш", command=self._open_selected_result).pack(side="left", padx=6)
        ttk.Button(controls, text="results папкасини очиш", command=lambda: self._open_path(self.project_root / "results")).pack(side="left")

        columns = ("path", "size", "modified")
        self.file_tree = ttk.Treeview(tab, columns=columns, show="headings")
        self.file_tree.heading("path", text="Нисбий йўл")
        self.file_tree.heading("size", text="Ҳажм")
        self.file_tree.heading("modified", text="Ўзгартирилган вақт")
        self.file_tree.column("path", width=760, anchor="w")
        self.file_tree.column("size", width=120, anchor="e")
        self.file_tree.column("modified", width=180, anchor="center")
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=scrollbar.set)
        self.file_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.file_tree.bind("<Double-1>", lambda _event: self._open_selected_result())

    def _build_log_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(tab, text="Журнал")
        self.log_text = scrolledtext.ScrolledText(
            tab,
            wrap="word",
            font=("Cascadia Mono", 9),
            state="disabled",
        )
        self.log_text.pack(fill="both", expand=True)

    def _build_statusbar(self) -> None:
        frame = ttk.Frame(self.root, padding=(18, 4, 18, 8))
        frame.pack(fill="x")
        ttk.Label(frame, textvariable=self.status_var).pack(side="left")
        ttk.Label(frame, text="AppliedMath v0.3.0 · фақат детерминистик модель").pack(side="right")

    def _set_busy(self, busy: bool, message: str | None = None) -> None:
        self._busy = busy
        for button in self._buttons:
            button.configure(state="disabled" if busy else "normal")
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()
        if message is not None:
            self.status_var.set(message)

    def _submit_task(
        self,
        label: str,
        worker: Callable[[], T],
        on_success: Callable[[T], None],
    ) -> None:
        if self._busy:
            self.status_var.set("Бошқа вазифа бажарилмоқда.")
            return
        self._set_busy(True, label)
        self._log(label)

        def target() -> None:
            try:
                self._task_queue.put(("ok", worker()))
            except Exception:
                self._task_queue.put(("error", traceback.format_exc()))

        threading.Thread(target=target, daemon=True).start()

        def poll() -> None:
            try:
                kind, payload = self._task_queue.get_nowait()
            except queue.Empty:
                self.root.after(100, poll)
                return
            self._set_busy(False)
            if kind == "ok":
                try:
                    on_success(payload)  # type: ignore[arg-type]
                except Exception:
                    self._handle_error(traceback.format_exc())
            else:
                self._handle_error(str(payload))

        self.root.after(100, poll)

    def open_benchmark_file(self) -> None:
        benchmarks_dir = self.project_root / "Data" / "benchmarks"
        initial_dir = benchmarks_dir if benchmarks_dir.is_dir() else self.project_root
        path_str = filedialog.askopenfilename(
            parent=self.root,
            title="Тармоқ очиш",
            initialdir=str(initial_dir),
            filetypes=[("Benchmark JSON", "*.json"), ("Барча файллар", "*.*")],
        )
        if not path_str:
            return
        path = Path(path_str)
        self._current_benchmark_path = path
        self._submit_task(
            f"{path.name} юкланмоқда ва ҳисобланмоқда...",
            lambda: solve_benchmark_at_path(path),
            self._display_snapshot,
        )

    def run_selected_benchmark(self) -> None:
        path = self._current_benchmark_path
        if path is None:
            messagebox.showwarning(
                "Тармоқ танланмади",
                "Аввал \"Файл > Тармоқ очиш\" орқали benchmark файлини танланг.",
                parent=self.root,
            )
            return
        self._submit_task(
            f"{path.name} қайта ҳисобланмоқда...",
            lambda: solve_benchmark_at_path(path),
            self._display_snapshot,
        )

    def _display_snapshot(self, snapshot: BenchmarkSnapshot) -> None:
        self.snapshot = snapshot
        model = snapshot.model
        self.benchmark_name_var.set(model.name)
        self.description_var.set(
            f"{benchmark_description_uz(model)}\n"
            f"Тузилма: {len(model.nodes)} тугун, {len(model.edges)} қирра, "
            f"{len(model.users)} истеъмолчи, {len(model.periods)} давр."
        )
        self.card_closed.set(
            f"{fraction_string(snapshot.closed_form.lambda_star)}\n({float(snapshot.closed_form.lambda_star):.9f})"
        )
        self.card_lp.set(f"{snapshot.stage1_lp.lambda_star:.9f}")
        self.card_theta.set(f"{snapshot.solution.stage2.weighted_satisfaction:.9f}")
        self.card_omega.set(f"{snapshot.solution.stage3.temporal_variation:.9f}")
        self.card_status.set("PASS" if snapshot.verification_passed else "FAIL")
        self.active_resource_var.set(
            "Фаол ресурслар: " + ", ".join(resource_label_uz(item) for item in snapshot.closed_form.active_resources)
        )

        self._replace_tree_rows(self.stage_tree, stage_rows(snapshot))
        self._replace_tree_rows(self.ratio_tree, ratio_rows(snapshot))
        self._replace_tree_rows(
            self.verify_tree,
            verification_rows(snapshot),
            tag_index=3,
        )
        users = users_with_activity(model)
        self.user_combo["values"] = users
        self.user_var.set(users[0] if users else "")
        self._draw_allocation_chart()
        self._draw_network()

        exact_difference = fraction_string(snapshot.operator_verification.maximum_absolute_difference)
        node_residual = fraction_string(snapshot.operator_verification.maximum_node_residual)
        self.verification_detail_var.set(
            f"λ* closed form = {fraction_string(snapshot.closed_form.lambda_star)}; "
            f"λ* LP = {snapshot.stage1_lp.lambda_star:.12g}; "
            f"абсолют фарқ = {snapshot.closed_form_lp_difference:.3e}. "
            f"Аниқ оператор–баланс фарқи = {exact_difference}; "
            f"аниқ тугун residual = {node_residual}; "
            f"3-босқич физик бузилиши = {snapshot.maximum_physical_violation:.3e}."
        )
        self.status_var.set(
            f"{model.name}: ҳисоблаш тугалланди — "
            f"{'PASS' if snapshot.verification_passed else 'FAIL'}"
        )
        self._log(
            f"{model.name}: λ*={float(snapshot.closed_form.lambda_star):.9f}, "
            f"θ*={snapshot.solution.stage2.weighted_satisfaction:.9f}, "
            f"Ω3={snapshot.solution.stage3.temporal_variation:.9f}, "
            f"status={'PASS' if snapshot.verification_passed else 'FAIL'}"
        )

    @staticmethod
    def _replace_tree_rows(
        tree: ttk.Treeview,
        rows: tuple[tuple[str, ...], ...],
        *,
        tag_index: int | None = None,
    ) -> None:
        tree.delete(*tree.get_children())
        for row in rows:
            tags: tuple[str, ...] = ()
            if tag_index is not None and len(row) > tag_index:
                tags = (str(row[tag_index]).lower(),)
            tree.insert("", "end", values=row, tags=tags)

    def _draw_allocation_chart(self) -> None:
        self.allocation_ax.clear()
        if self.snapshot is None or not self.user_var.get():
            self.allocation_ax.set_title("Ҳисоблаш натижаси мавжуд эмас")
            self.allocation_canvas.draw_idle()
            return
        user = self.user_var.get()
        periods, stage1, stage2, stage3 = period_series(self.snapshot, user)
        x = np.arange(len(periods))
        self.allocation_ax.plot(x, stage1, marker="o", label="1-босқич")
        self.allocation_ax.plot(x, stage2, marker="s", label="2-босқич")
        self.allocation_ax.plot(x, stage3, marker="^", label="3-босқич")
        self.allocation_ax.set_xticks(x, periods)
        self.allocation_ax.set_ylim(0.0, 1.05)
        self.allocation_ax.set_xlabel("Давр")
        self.allocation_ax.set_ylabel("Талабни қондириш нисбати")
        self.allocation_ax.set_title(f"{user}: лексикографик тақсимот профили")
        self.allocation_ax.grid(True, alpha=0.3)
        self.allocation_ax.legend(loc="best")
        self.allocation_canvas.draw_idle()

    @staticmethod
    def _tree_positions(graph: nx.DiGraph, source: str) -> dict[str, tuple[float, float]]:
        depth = nx.single_source_shortest_path_length(graph, source)
        levels: dict[int, list[str]] = {}
        for node in nx.topological_sort(graph):
            levels.setdefault(depth[node], []).append(node)
        positions: dict[str, tuple[float, float]] = {}
        for level, nodes in sorted(levels.items()):
            xs = np.linspace(0.08, 0.92, max(1, len(nodes)))
            if len(nodes) == 1:
                xs = np.asarray([0.5])
            for x, node in zip(xs, nodes):
                positions[node] = (float(x), float(-level))
        return positions

    def _draw_network(self) -> None:
        self.network_ax.clear()
        if self.snapshot is None:
            self.network_ax.set_title("Ҳисоблаш натижаси мавжуд эмас")
            self.network_canvas.draw_idle()
            return
        model = self.snapshot.model
        graph = build_graph(model)
        if model.node_positions is not None:
            # Use the real canal-system geometry when the benchmark ships one,
            # instead of a generic depth-level layout that does not reflect
            # the actual physical network.
            positions = {node: model.node_positions[node] for node in graph.nodes}
        else:
            positions = self._tree_positions(graph, model.source)
        node_sizes = [1000 if node == model.source else 760 for node in graph.nodes]
        nx.draw_networkx_nodes(graph, positions, node_size=node_sizes, ax=self.network_ax)
        nx.draw_networkx_labels(graph, positions, font_size=9, ax=self.network_ax)
        nx.draw_networkx_edges(
            graph,
            positions,
            arrows=True,
            arrowsize=18,
            width=1.4,
            ax=self.network_ax,
        )
        edge_labels = {(edge.tail, edge.head): edge.edge_id for edge in model.edges}
        nx.draw_networkx_edge_labels(
            graph,
            positions,
            edge_labels=edge_labels,
            font_size=8,
            rotate=False,
            ax=self.network_ax,
        )
        self.network_ax.set_title(f"{model.name}: йўналтирилган дарахт тармоғи")
        self.network_ax.axis("off")
        self.network_canvas.draw_idle()

    def save_current_benchmark_result(self) -> None:
        if self.snapshot is None or self._current_benchmark_path is None:
            messagebox.showwarning(
                "Тармоқ танланмади",
                "Аввал \"Файл > Тармоқ очиш\" орқали benchmark файлини очинг ва "
                "ҳисоблаш тугашини кутинг.",
                parent=self.root,
            )
            return
        default_dir = self.project_root / "results"
        initial_dir = default_dir if default_dir.is_dir() else self.project_root
        output_dir = filedialog.askdirectory(
            parent=self.root,
            title="Натижани сақлаш — папка танланг",
            initialdir=str(initial_dir),
            mustexist=False,
        )
        if not output_dir:
            return
        path = self._current_benchmark_path
        self._submit_task(
            f"{self.benchmark_name_var.get()} натижалари сақланмоқда...",
            lambda: save_benchmark_result(self.project_root, path, output_dir),
            self._save_result_ready,
        )

    def _save_result_ready(self, summary: dict[str, object]) -> None:
        self._refresh_result_files()
        status = str(summary.get("verification_status", "UNKNOWN"))
        folder = str(summary.get("output_folder", "?"))
        self.status_var.set(f"Натижа сақланди: {status}")
        self._log("Натижа сақланди:\n" + "\n".join(f"  {key}: {value}" for key, value in summary.items()))
        messagebox.showinfo(
            "Натижа сақланди",
            f"Тармоқ, профиль, матрица ва верификация натижалари шу папкага сақланди:\n{folder}\n\n"
            f"Verification status: {status}",
            parent=self.root,
        )

    def generate_article_outputs(self) -> None:
        self._submit_task(
            "Барча жадвал, figure-data ва журнал расмлари қайта яратилмоқда...",
            lambda: generate_article_results(self.project_root),
            self._article_outputs_ready,
        )

    def _article_outputs_ready(self, summary: dict[str, object]) -> None:
        self._refresh_result_files()
        status = str(summary.get("verification_status", "UNKNOWN"))
        self.status_var.set(f"Мақола натижалари яратилди: {status}")
        self._log("Мақола натижалари:\n" + "\n".join(f"  {key}: {value}" for key, value in summary.items()))
        warnings = summary.get("figure_warnings") or []
        message = (
            "Жадваллар, figure-data ва PNG расмлар results/ папкасида "
            "(ҳар бир тармоқ ўз алоҳида папкасида) қайта яратилди.\n"
            f"Verification status: {status}"
        )
        if warnings:
            self._log("ОГОҲЛАНТИРИШ — қуйидагилар бошқа дастур томонидан очиқ бўлгани учун "
                       "тўлиқ янгиланмади:\n" + "\n".join(f"  {item}" for item in warnings))
            message += (
                "\n\nОГОҲЛАНТИРИШ: баъзи файл/папкалар бошқа дастур (расм кўрувчи, Explorer "
                "ёки IDE) томонидан очиқ бўлгани учун тўлиқ янгиланмади. Уларни ёпиб, "
                "натижаларни қайта яратинг. Батафсил: Журнал вкладкаси."
            )
        messagebox.showinfo("Натижалар тайёр", message, parent=self.root)

    def run_test_suite(self) -> None:
        self._submit_task(
            "Pytest автоматик текширувлари бажарилмоқда...",
            lambda: run_tests(self.project_root),
            self._tests_ready,
        )

    def _tests_ready(self, result: tuple[int, str]) -> None:
        return_code, output = result
        self._log("Pytest натижаси:\n" + (output or "(output йўқ)"))
        if return_code == 0:
            self.status_var.set("Барча автоматик тестлар PASS")
            messagebox.showinfo("Тестлар", "Барча автоматик тестлар муваффақиятли ўтди.", parent=self.root)
        else:
            self.status_var.set("Тестларда хато бор")
            messagebox.showerror("Тестлар", "Тестлардан камида бири ўтмади. Журнал вкладкасини текширинг.", parent=self.root)

    def export_current(self) -> None:
        if self.snapshot is None:
            messagebox.showwarning("CSV/Excel экспорт", "Аввал назорат мисолини ечинг.", parent=self.root)
            return
        try:
            ratios_path, verification_path = export_snapshot(self.snapshot, self.project_root)
        except Exception:
            self._handle_error(traceback.format_exc())
            return
        self._refresh_result_files()
        self.status_var.set("Жорий назорат мисоли CSV/Excel файлларга экспорт қилинди")
        self._log(f"CSV/Excel экспорт: {ratios_path}\nCSV/Excel экспорт: {verification_path}")
        messagebox.showinfo(
            "CSV/Excel экспорт",
            f"Файллар сақланди (ҳар бирининг excel/ нусхаси ҳам бор):\n{ratios_path}\n{verification_path}",
            parent=self.root,
        )

    def _refresh_result_files(self) -> None:
        if not hasattr(self, "file_tree"):
            return
        self.file_tree.delete(*self.file_tree.get_children())
        for item in result_files(self.project_root):
            size = self._format_bytes(item.size_bytes)
            self.file_tree.insert("", "end", values=(item.relative_path, size, item.modified_at))

    @staticmethod
    def _format_bytes(size: int) -> str:
        value = float(size)
        for unit in ("B", "KB", "MB", "GB"):
            if value < 1024.0 or unit == "GB":
                return f"{value:.1f} {unit}"
            value /= 1024.0
        return f"{size} B"

    def _open_selected_result(self) -> None:
        selection = self.file_tree.selection()
        if not selection:
            return
        values = self.file_tree.item(selection[0], "values")
        if not values:
            return
        self._open_path(self.project_root / str(values[0]))

    @staticmethod
    def _open_path(path: Path) -> None:
        path = path.resolve()
        if not path.exists():
            raise FileNotFoundError(path)
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def _log(self, text: str) -> None:
        if not hasattr(self, "log_text"):
            return
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text.rstrip() + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _handle_error(self, details: str) -> None:
        self._set_busy(False, "Хато юз берди")
        self._log(details)
        messagebox.showerror(
            "Хато",
            "Вазифани бажаришда хато юз берди. Батафсил маълумот Журнал вкладкасида.",
            parent=self.root,
        )

    def _report_callback_exception(self, exc_type: type[BaseException], exc_value: BaseException, exc_tb: object) -> None:
        details = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        self._handle_error(details)

    def _show_boundary(self) -> None:
        messagebox.showinfo(
            "Модель чегараси",
            "Ушбу desktop GUI аниқ параметрларга эга детерминистик rooted-tree "
            "benchmark’ларни ечади. Сценарийли, стохастик ва робаст оптималлаштириш "
            "ишлатилмайди. Натижалар математик верификацияга тегишли бўлиб, дала "
            "валидацияси ёки муайян канал тизимининг эксплуатацион баҳоси эмас.",
            parent=self.root,
        )

    def _show_about(self) -> None:
        messagebox.showinfo(
            "Дастур ҳақида",
            "AppliedMath LexFlow Desktop v0.3.0\n\n"
            "1-босқич: max–min адолат ва ёпиқ ечим.\n"
            "2-босқич: вазнланган мавсумий қониқиш.\n"
            "3-босқич: вақт бўйича тақсимот вариациясини минималлаштириш.\n\n"
            "GUI ва CLI бир хил appliedmath_lexflow solver пакетидан фойдаланади.",
            parent=self.root,
        )


def main(project_root: str | Path | None = None) -> int:
    try:
        resolved_root = find_project_root(project_root or Path.cwd())
        root = tk.Tk()
    except Exception as exc:
        print(f"Desktop GUI could not start: {exc}", file=sys.stderr)
        return 1

    LexFlowDesktopApp(root, resolved_root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
