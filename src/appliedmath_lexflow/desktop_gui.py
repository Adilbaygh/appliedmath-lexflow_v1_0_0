"""Tk desktop interface for the deterministic AppliedMath benchmark project."""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

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
    benchmark_description,
    export_snapshot,
    find_project_root,
    fraction_string,
    generate_article_results,
    period_series,
    ratio_rows,
    resource_label,
    result_files,
    run_tests,
    save_benchmark_result,
    solve_benchmark_at_path,
    stage_rows,
    users_with_activity,
    verification_rows,
)
from .i18n import LANGUAGE_NAMES, SUPPORTED_LANGUAGES, tr
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
        self._log_entries: list[str] = []
        self.language = "uz"
        self.language_var = tk.StringVar(value=self.language)

        self.root.title(self._t("window_title"))
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
        self.root.bind("<Control-l>", lambda _event: self._toggle_language())
        self.root.bind("<Control-L>", lambda _event: self._toggle_language())

        self.status_var = tk.StringVar(value=self._t("ready"))
        self.benchmark_name_var = tk.StringVar(value=self._t("no_network"))
        self.user_var = tk.StringVar()
        self.description_var = tk.StringVar(value=self._t("choose_hint"))

        self._build_menu()
        self._build_header()
        self._build_controls()
        self._build_notebook()
        self._build_statusbar()
        self._refresh_result_files()

        self._log(self._t("project_log", path=self.project_root))
        self._log(self._t("boundary_log"))

    def _t(self, key: str, **values: object) -> str:
        return tr(key, self.language, **values)

    def _toggle_language(self) -> None:
        self._switch_language("en" if self.language == "uz" else "uz")

    def _switch_language(self, language: str) -> None:
        if language == self.language:
            return
        if self._busy:
            self.language_var.set(self.language)
            self.status_var.set(self._t("busy"))
            return
        self.language = language
        self.language_var.set(language)
        self.root.title(self._t("window_title"))
        for child in self.root.winfo_children():
            child.destroy()
        self._buttons.clear()
        self.status_var.set(self._t("ready"))
        self.description_var.set(self._t("choose_hint"))
        if self.snapshot is None:
            self.benchmark_name_var.set(self._t("no_network"))
        self._build_menu()
        self._build_header()
        self._build_controls()
        self._build_notebook()
        self._build_statusbar()
        self._refresh_result_files()
        if self.snapshot is not None:
            self._display_snapshot(self.snapshot, log_result=False)

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
        file_menu.add_command(label=self._t("menu_open"), command=self.open_benchmark_file)
        file_menu.add_separator()
        file_menu.add_command(label=self._t("menu_resolve"), command=self.run_selected_benchmark)
        file_menu.add_command(label=self._t("menu_save"), command=self.save_current_benchmark_result)
        file_menu.add_separator()
        # Everything below is independent of whatever benchmark (if any) is
        # currently open in the GUI — it works even with nothing loaded.
        file_menu.add_command(
            label=self._t("menu_generate"),
            command=self.generate_article_outputs,
        )
        file_menu.add_command(label=self._t("menu_tests"), command=self.run_test_suite)
        file_menu.add_separator()
        file_menu.add_command(label=self._t("menu_results"), command=lambda: self._open_path(self.project_root / "results"))
        file_menu.add_command(label=self._t("menu_project"), command=lambda: self._open_path(self.project_root))
        file_menu.add_separator()
        file_menu.add_command(label=self._t("menu_exit"), command=self.root.destroy)
        menu.add_cascade(label=self._t("menu_file"), menu=file_menu)

        language_menu = tk.Menu(menu, tearoff=False)
        for language in SUPPORTED_LANGUAGES:
            language_menu.add_radiobutton(
                label=LANGUAGE_NAMES[language],
                variable=self.language_var,
                value=language,
                command=lambda selected=language: self._switch_language(selected),
            )
        menu.add_cascade(label=self._t("menu_language"), menu=language_menu)

        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(label=self._t("menu_boundary"), command=self._show_boundary)
        help_menu.add_command(label=self._t("menu_about"), command=self._show_about)
        menu.add_cascade(label=self._t("menu_help"), menu=help_menu)
        self.root.configure(menu=menu)

    def _build_header(self) -> None:
        frame = ttk.Frame(self.root, padding=(18, 14, 18, 8))
        frame.pack(fill="x")
        ttk.Label(
            frame,
            text=self._t("header_title"),
            style="Title.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            frame,
            text=self._t("header_subtitle"),
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(3, 0))

    def _button(self, parent: tk.Misc, text: str, command: Callable[[], None]) -> ttk.Button:
        button = ttk.Button(parent, text=text, command=command)
        self._buttons.append(button)
        return button

    def _build_controls(self) -> None:
        controls = ttk.Frame(self.root, padding=(18, 6, 18, 10))
        controls.pack(fill="x")
        ttk.Label(controls, text=self._t("benchmark"), style="Section.TLabel").pack(side="left")
        self._button(controls, self._t("open"), self.open_benchmark_file).pack(side="left", padx=(8, 8))
        ttk.Label(
            controls, textvariable=self.benchmark_name_var, style="Section.TLabel"
        ).pack(side="left", padx=(0, 12))

        self._button(controls, self._t("solve"), self.run_selected_benchmark).pack(side="left", padx=4)
        self._button(controls, self._t("save_result"), self.save_current_benchmark_result).pack(side="left", padx=4)
        self._button(controls, self._t("regenerate_all"), self.generate_article_outputs).pack(side="left", padx=4)
        self._button(controls, self._t("tests"), self.run_test_suite).pack(side="left", padx=4)
        self._button(controls, self._t("export"), self.export_current).pack(side="left", padx=4)
        self._button(controls, self._t("results_folder"), lambda: self._open_path(self.project_root / "results")).pack(side="right", padx=4)

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
        self.notebook.add(tab, text=self._t("tab_overview"))

        description_box = ttk.LabelFrame(tab, text=self._t("description"), padding=10)
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
        self.card_closed = MetricCard(cards, self._t("card_closed"))
        self.card_lp = MetricCard(cards, self._t("card_lp"))
        self.card_theta = MetricCard(cards, self._t("card_stage2"))
        self.card_omega = MetricCard(cards, self._t("card_stage3"))
        self.card_status = MetricCard(cards, self._t("card_verification"))
        for index, card in enumerate(
            (self.card_closed, self.card_lp, self.card_theta, self.card_omega, self.card_status)
        ):
            card.grid(row=0, column=index, sticky="nsew", padx=5)

        stage_box = ttk.LabelFrame(tab, text=self._t("stages"), padding=8)
        stage_box.pack(fill="both", expand=True)
        columns = ("stage", "min", "satisfaction", "variation", "status")
        self.stage_tree = ttk.Treeview(stage_box, columns=columns, show="headings", height=8)
        headings = {
            "stage": self._t("h_stage"),
            "min": self._t("h_min"),
            "satisfaction": self._t("h_satisfaction"),
            "variation": self._t("h_variation"),
            "status": self._t("h_solver"),
        }
        widths = {"stage": 150, "min": 170, "satisfaction": 210, "variation": 190, "status": 140}
        for column in columns:
            self.stage_tree.heading(column, text=headings[column])
            self.stage_tree.column(column, width=widths[column], anchor="center")
        self.stage_tree.pack(fill="both", expand=True)

        self.active_resource_var = tk.StringVar(value=self._t("active_resources", resources="—"))
        ttk.Label(tab, textvariable=self.active_resource_var, padding=(3, 8, 3, 0)).pack(anchor="w")

    def _build_allocations_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text=self._t("tab_allocations"))
        paned = ttk.Panedwindow(tab, orient="horizontal")
        paned.pack(fill="both", expand=True)

        table_frame = ttk.LabelFrame(paned, text=self._t("records"), padding=6)
        chart_frame = ttk.LabelFrame(paned, text=self._t("profile"), padding=6)
        paned.add(table_frame, weight=3)
        paned.add(chart_frame, weight=2)

        columns = ("period", "user", "demand", "s1", "s2", "s3")
        self.ratio_tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        headings = {
            "period": self._t("h_period"),
            "user": self._t("h_user"),
            "demand": self._t("h_demand"),
            "s1": self._t("stage1"),
            "s2": self._t("stage2"),
            "s3": self._t("stage3"),
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
        ttk.Label(user_controls, text=self._t("user")).pack(side="left")
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
        self.notebook.add(tab, text=self._t("tab_verification"))
        columns = ("check", "value", "criterion", "status")
        self.verify_tree = ttk.Treeview(tab, columns=columns, show="headings")
        headings = {
            "check": self._t("h_check"),
            "value": self._t("h_value"),
            "criterion": self._t("h_criterion"),
            "status": self._t("h_result"),
        }
        widths = {"check": 360, "value": 220, "criterion": 300, "status": 100}
        for column in columns:
            self.verify_tree.heading(column, text=headings[column])
            self.verify_tree.column(column, width=widths[column], anchor="w" if column == "check" else "center")
        self.verify_tree.tag_configure("pass", foreground="#176b36")
        self.verify_tree.tag_configure("fail", foreground="#a11d1d")
        self.verify_tree.pack(fill="both", expand=True)

        detail_frame = ttk.LabelFrame(tab, text=self._t("math_details"), padding=8)
        detail_frame.pack(fill="x", pady=(10, 0))
        self.verification_detail_var = tk.StringVar(value="—")
        ttk.Label(detail_frame, textvariable=self.verification_detail_var, wraplength=1180, justify="left").pack(anchor="w")

    def _build_network_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(tab, text=self._t("tab_network"))
        self.network_figure = Figure(figsize=(9.0, 5.2), dpi=100, constrained_layout=True)
        self.network_ax = self.network_figure.add_subplot(111)
        self.network_canvas = FigureCanvasTkAgg(self.network_figure, master=tab)
        self.network_canvas.get_tk_widget().pack(fill="both", expand=True)
        toolbar = NavigationToolbar2Tk(self.network_canvas, tab, pack_toolbar=False)
        toolbar.update()
        toolbar.pack(fill="x")

    def _build_files_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text=self._t("tab_files"))
        controls = ttk.Frame(tab)
        controls.pack(fill="x", pady=(0, 8))
        ttk.Button(controls, text=self._t("refresh"), command=self._refresh_result_files).pack(side="left")
        ttk.Button(controls, text=self._t("open_selected"), command=self._open_selected_result).pack(side="left", padx=6)
        ttk.Button(controls, text=self._t("open_results"), command=lambda: self._open_path(self.project_root / "results")).pack(side="left")

        columns = ("path", "size", "modified")
        self.file_tree = ttk.Treeview(tab, columns=columns, show="headings")
        self.file_tree.heading("path", text=self._t("h_path"))
        self.file_tree.heading("size", text=self._t("h_size"))
        self.file_tree.heading("modified", text=self._t("h_modified"))
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
        self.notebook.add(tab, text=self._t("tab_log"))
        self.log_text = scrolledtext.ScrolledText(
            tab,
            wrap="word",
            font=("Cascadia Mono", 9),
            state="disabled",
        )
        self.log_text.pack(fill="both", expand=True)
        if self._log_entries:
            self.log_text.configure(state="normal")
            self.log_text.insert("end", "\n".join(self._log_entries) + "\n")
            self.log_text.configure(state="disabled")

    def _build_statusbar(self) -> None:
        frame = ttk.Frame(self.root, padding=(18, 4, 18, 8))
        frame.pack(fill="x")
        ttk.Label(frame, textvariable=self.status_var).pack(side="left")
        ttk.Label(frame, text=self._t("footer")).pack(side="right")

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
            self.status_var.set(self._t("busy"))
            return
        self._set_busy(True, label)
        self._log(label)

        def target() -> None:
            try:
                self._task_queue.put(("ok", worker()))
            except Exception:  # noqa: BLE001 - GUI worker must surface any task failure
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
                except Exception:  # noqa: BLE001 - callback failures belong in the GUI log
                    self._handle_error(traceback.format_exc())
            else:
                self._handle_error(str(payload))

        self.root.after(100, poll)

    def open_benchmark_file(self) -> None:
        benchmarks_dir = self.project_root / "Data" / "benchmarks"
        initial_dir = benchmarks_dir if benchmarks_dir.is_dir() else self.project_root
        path_str = filedialog.askopenfilename(
            parent=self.root,
            title=self._t("dialog_open"),
            initialdir=str(initial_dir),
            filetypes=[("Benchmark JSON", "*.json"), (self._t("all_files"), "*.*")],
        )
        if not path_str:
            return
        path = Path(path_str)
        self._current_benchmark_path = path
        self._submit_task(
            self._t("loading", name=path.name),
            lambda: solve_benchmark_at_path(path),
            self._display_snapshot,
        )

    def run_selected_benchmark(self) -> None:
        path = self._current_benchmark_path
        if path is None:
            messagebox.showwarning(
                self._t("warning_no_network"),
                self._t("warning_choose"),
                parent=self.root,
            )
            return
        self._submit_task(
            self._t("recalculating", name=path.name),
            lambda: solve_benchmark_at_path(path),
            self._display_snapshot,
        )

    def _display_snapshot(self, snapshot: BenchmarkSnapshot, *, log_result: bool = True) -> None:
        self.snapshot = snapshot
        model = snapshot.model
        self.benchmark_name_var.set(model.name)
        self.description_var.set(
            f"{benchmark_description(model, self.language)}\n"
            + self._t(
                "structure",
                nodes=len(model.nodes),
                edges=len(model.edges),
                users=len(model.users),
                periods=len(model.periods),
            )
        )
        self.card_closed.set(
            f"{fraction_string(snapshot.closed_form.lambda_star)}\n({float(snapshot.closed_form.lambda_star):.9f})"
        )
        self.card_lp.set(f"{snapshot.stage1_lp.lambda_star:.9f}")
        self.card_theta.set(f"{snapshot.solution.stage2.weighted_satisfaction:.9f}")
        self.card_omega.set(f"{snapshot.solution.stage3.temporal_variation:.9f}")
        self.card_status.set("PASS" if snapshot.verification_passed else "FAIL")
        self.active_resource_var.set(
            self._t(
                "active_resources",
                resources=", ".join(
                    resource_label(item, self.language)
                    for item in snapshot.closed_form.active_resources
                ),
            )
        )

        self._replace_tree_rows(self.stage_tree, stage_rows(snapshot, self.language))
        self._replace_tree_rows(self.ratio_tree, ratio_rows(snapshot))
        self._replace_tree_rows(
            self.verify_tree,
            verification_rows(snapshot, language=self.language),
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
            self._t(
                "verification_detail",
                closed=fraction_string(snapshot.closed_form.lambda_star),
                lp=f"{snapshot.stage1_lp.lambda_star:.12g}",
                difference=f"{snapshot.closed_form_lp_difference:.3e}",
                operator=exact_difference,
                residual=node_residual,
                physical=f"{snapshot.maximum_physical_violation:.3e}",
            )
        )
        status = "PASS" if snapshot.verification_passed else "FAIL"
        self.status_var.set(self._t("completed", name=model.name, status=status))
        if log_result:
            self._log(
                f"{model.name}: λ*={float(snapshot.closed_form.lambda_star):.9f}, "
                f"θ*={snapshot.solution.stage2.weighted_satisfaction:.9f}, "
                f"Ω3={snapshot.solution.stage3.temporal_variation:.9f}, "
                f"status={status}"
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
            self.allocation_ax.set_title(self._t("no_results"))
            self.allocation_canvas.draw_idle()
            return
        user = self.user_var.get()
        periods, stage1, stage2, stage3 = period_series(self.snapshot, user)
        x = np.arange(len(periods))
        self.allocation_ax.plot(x, stage1, marker="o", label=self._t("stage1"))
        self.allocation_ax.plot(x, stage2, marker="s", label=self._t("stage2"))
        self.allocation_ax.plot(x, stage3, marker="^", label=self._t("stage3"))
        self.allocation_ax.set_xticks(x, periods)
        self.allocation_ax.set_ylim(0.0, 1.05)
        self.allocation_ax.set_xlabel(self._t("chart_xlabel"))
        self.allocation_ax.set_ylabel(self._t("chart_ylabel"))
        self.allocation_ax.set_title(self._t("chart_title", user=user))
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
            self.network_ax.set_title(self._t("no_results"))
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
        self.network_ax.set_title(self._t("network_title", name=model.name))
        self.network_ax.axis("off")
        self.network_canvas.draw_idle()

    def save_current_benchmark_result(self) -> None:
        if self.snapshot is None or self._current_benchmark_path is None:
            messagebox.showwarning(
                self._t("warning_no_network"),
                self._t("warning_open_first"),
                parent=self.root,
            )
            return
        default_dir = self.project_root / "results"
        initial_dir = default_dir if default_dir.is_dir() else self.project_root
        output_dir = filedialog.askdirectory(
            parent=self.root,
            title=self._t("choose_output"),
            initialdir=str(initial_dir),
            mustexist=False,
        )
        if not output_dir:
            return
        path = self._current_benchmark_path
        self._submit_task(
            self._t("saving", name=self.benchmark_name_var.get()),
            lambda: save_benchmark_result(self.project_root, path, output_dir),
            self._save_result_ready,
        )

    def _save_result_ready(self, summary: dict[str, object]) -> None:
        self._refresh_result_files()
        status = str(summary.get("verification_status", "UNKNOWN"))
        folder = str(summary.get("output_folder", "?"))
        self.status_var.set(self._t("saved", status=status))
        self._log(self._t("saved_title") + ":\n" + "\n".join(f"  {key}: {value}" for key, value in summary.items()))
        messagebox.showinfo(
            self._t("saved_title"),
            self._t("saved_message", folder=folder, status=status),
            parent=self.root,
        )

    def generate_article_outputs(self) -> None:
        self._submit_task(
            self._t("generating"),
            lambda: generate_article_results(self.project_root),
            self._article_outputs_ready,
        )

    def _article_outputs_ready(self, summary: dict[str, object]) -> None:
        self._refresh_result_files()
        status = str(summary.get("verification_status", "UNKNOWN"))
        self.status_var.set(self._t("generated", status=status))
        self._log(
            self._t("generated", status=status)
            + ":\n"
            + "\n".join(f"  {key}: {value}" for key, value in summary.items())
        )
        warnings = summary.get("figure_warnings") or []
        message = self._t("generated_message", status=status)
        if warnings:
            self._log(self._t("generated_warning") + "\n" + "\n".join(f"  {item}" for item in warnings))
            message += "\n\n" + self._t("generated_warning")
        messagebox.showinfo(self._t("generated_title"), message, parent=self.root)

    def run_test_suite(self) -> None:
        self._submit_task(
            self._t("testing"),
            lambda: run_tests(self.project_root),
            self._tests_ready,
        )

    def _tests_ready(self, result: tuple[int, str]) -> None:
        return_code, output = result
        self._log("Pytest:\n" + (output or "(no output)"))
        if return_code == 0:
            self.status_var.set(self._t("tests_passed"))
            messagebox.showinfo(self._t("tests"), self._t("tests_passed_message"), parent=self.root)
        else:
            self.status_var.set(self._t("tests_failed"))
            messagebox.showerror(self._t("tests"), self._t("tests_failed_message"), parent=self.root)

    def export_current(self) -> None:
        if self.snapshot is None:
            messagebox.showwarning(self._t("export"), self._t("export_first"), parent=self.root)
            return
        try:
            ratios_path, verification_path = export_snapshot(
                self.snapshot, self.project_root, self.language
            )
        except Exception:  # noqa: BLE001 - export errors are reported in the GUI
            self._handle_error(traceback.format_exc())
            return
        self._refresh_result_files()
        self.status_var.set(self._t("exported"))
        self._log(f"CSV/Excel: {ratios_path}\nCSV/Excel: {verification_path}")
        messagebox.showinfo(
            self._t("export"),
            self._t("exported_message", ratios=ratios_path, verification=verification_path),
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
        normalized = text.rstrip()
        self._log_entries.append(normalized)
        if not hasattr(self, "log_text"):
            return
        self.log_text.configure(state="normal")
        self.log_text.insert("end", normalized + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _handle_error(self, details: str) -> None:
        self._set_busy(False, self._t("error_status"))
        self._log(details)
        messagebox.showerror(
            self._t("error_title"),
            self._t("error_message"),
            parent=self.root,
        )

    def _report_callback_exception(self, exc_type: type[BaseException], exc_value: BaseException, exc_tb: object) -> None:
        details = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        self._handle_error(details)

    def _show_boundary(self) -> None:
        messagebox.showinfo(
            self._t("boundary_title"),
            self._t("boundary_message"),
            parent=self.root,
        )

    def _show_about(self) -> None:
        messagebox.showinfo(
            self._t("about_title"),
            self._t("about_message"),
            parent=self.root,
        )


def main(project_root: str | Path | None = None) -> int:
    try:
        resolved_root = find_project_root(project_root or Path.cwd())
        root = tk.Tk()
    except Exception as exc:  # noqa: BLE001 - startup must fail with a readable message
        print(f"Desktop GUI could not start: {exc}", file=sys.stderr)
        return 1

    LexFlowDesktopApp(root, resolved_root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
