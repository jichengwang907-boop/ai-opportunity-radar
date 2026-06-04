from __future__ import annotations

import csv
import ctypes
import json
import os
import queue
import re
import runpy
import shutil
import subprocess
import sys
import threading
import time
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus


def enable_windows_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    try:
        user32 = ctypes.windll.user32
        user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        user32.SetProcessDpiAwarenessContext.restype = ctypes.c_bool
        if user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return
    except (AttributeError, OSError, ValueError):
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except (AttributeError, OSError, ValueError):
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError, ValueError):
        pass


enable_windows_dpi_awareness()

import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk


def resolve_root() -> Path:
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates = [exe_dir, exe_dir.parent, Path.cwd()]
    else:
        candidates = [Path(__file__).resolve().parents[1], Path.cwd()]
    for candidate in candidates:
        if (candidate / "scripts").is_dir() and (candidate / "config.realtime-ai-platforms.json").is_file():
            return candidate
    return candidates[0]


def resolve_python_command() -> list[str]:
    if not getattr(sys, "frozen", False):
        return [str(Path(sys.executable))]
    return [str(Path(sys.executable)), "--desktop-child"]


def python_cmd(*args: str) -> list[str]:
    return [*PYTHON_CMD, *args]


ROOT = resolve_root()
PYTHON_CMD = resolve_python_command()
APP_TITLE = "AI 机会雷达"
FONT_FAMILY = "Microsoft YaHei UI"
MONO_FONT_FAMILY = "Consolas"
COLORS = {
    "bg": "#e9f0f5",
    "left_bg": "#e9f4ef",
    "right_bg": "#edf2fb",
    "card": "#ffffff",
    "card_warm": "#fffaf2",
    "card_mint": "#f1fbf6",
    "card_lilac": "#f7f3ff",
    "card_blue": "#f5f9ff",
    "text": "#172033",
    "muted": "#667085",
    "line": "#d9e2ec",
    "header": "#111827",
    "header_2": "#1f2937",
    "accent": "#2563eb",
    "accent_hover": "#1d4ed8",
    "accent_soft": "#e8f1ff",
    "blue_soft": "#eff6ff",
    "green_soft": "#ecfdf3",
    "amber_soft": "#fff7ed",
    "violet_soft": "#f5f3ff",
    "success": "#059669",
    "warning": "#d97706",
    "console": "#111827",
    "console_text": "#dbeafe",
}

SEARCH_COLUMNS = [
    "source",
    "query",
    "title",
    "url",
    "rank",
    "result_count",
    "search_volume",
    "snippet",
    "price",
    "currency",
    "seller",
    "rating",
    "review_count",
    "collected_at",
    "signal_type",
    "buyer_intent_score",
    "pain_score",
    "source_confidence",
    "commercial_relevance",
]

PRODUCT_COLUMNS = [
    "source",
    "product_id",
    "title",
    "url",
    "price",
    "currency",
    "seller",
    "category",
    "stock_status",
    "rating",
    "review_count",
    "sales_volume",
    "last_updated",
    "collected_at",
    "signal_type",
    "buyer_intent_score",
    "pain_score",
    "source_confidence",
    "commercial_relevance",
]

EXTERNAL_COLUMNS = [
    "record_type",
    "source",
    "query",
    "title",
    "url",
    "rank",
    "result_count",
    "search_volume",
    "snippet",
    "product_id",
    "price",
    "currency",
    "seller",
    "category",
    "stock_status",
    "rating",
    "review_count",
    "sales_volume",
    "last_updated",
    "collected_at",
    "signal_type",
    "buyer_intent_score",
    "pain_score",
    "source_confidence",
    "commercial_relevance",
    "metric_name",
    "metric_value",
    "notes",
]

KEEP_ACTIONS = {"重点研究", "保留", "观察"}

PRODUCT_DATA_TERMS = (
    "catalog",
    "pim",
    "feed",
    "shopify",
    "odoo",
    "woocommerce",
    "marketplace",
    "sku",
    "商品",
    "产品",
    "资料",
    "多渠道",
    "plytix",
    "foxclipper",
    "channable",
    "datafeedwatch",
    "mergado",
    "sales layer",
    "syncspider",
    "toriut",
    "channelengine",
    "on page",
)

INVOICE_TERMS = (
    "invoice",
    "receipt",
    "accounts payable",
    " ap ",
    "autoentry",
    "veryfi",
    "lightyear",
    "docuclipper",
    "fidesic",
    "yooz",
    "softco",
    "fraxion",
    "predictap",
    "procurify",
    "papersave",
    "发票",
    "票据",
    "流水",
    "税表",
    "银行",
    "财务",
    "会计",
    "ap",
    "quickbooks",
    "xero",
    "采购",
)

EMAIL_DOC_TERMS = (
    "email",
    "mail",
    "parsio",
    "docparser",
    "parseur",
    "mailparser",
    "airparser",
    "parsedoc",
    "邮件",
    "附件",
    "询盘",
)


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "--desktop-child":
        return run_desktop_child(sys.argv[2:])
    if "--smoke-test" in sys.argv:
        print(json.dumps(read_dashboard_summary(), ensure_ascii=False, indent=2))
        return 0
    app = DesktopApp()
    app.mainloop()
    return 0


def run_desktop_child(args: list[str]) -> int:
    script = (ROOT / args[0]).resolve()
    if not script.is_file() or ROOT not in script.parents:
        raise RuntimeError(f"Invalid desktop child script: {script}")
    previous_argv = sys.argv[:]
    sys.argv = [str(script), *args[1:]]
    for entry in (str(ROOT / "scripts"), str(ROOT)):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    try:
        runpy.run_path(str(script), run_name="__main__")
    except SystemExit as exc:
        if exc.code is None:
            return 0
        if isinstance(exc.code, int):
            return exc.code
        print(exc.code)
        return 1
    finally:
        sys.argv = previous_argv
    return 0


class DesktopApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1500x880")
        self.minsize(1180, 760)
        self.configure(bg=COLORS["bg"])

        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.running = False
        self.fast_mode = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="就绪")
        self.snapshot_var = tk.StringVar(value="暂无")
        self.top_var = tk.StringVar(value="暂无")
        self.signals_var = tk.StringVar(value="0 搜索 / 0 产品")
        self.external_var = tk.StringVar(value="0 行 / 暂无")

        self._configure_dpi_and_fonts()
        self._configure_style()
        self._build_layout()
        self.refresh_summary()
        self.after(0, self._open_with_room)
        self.after(120, self._drain_events)

    def _open_with_room(self) -> None:
        try:
            if self.winfo_screenwidth() >= 1400 and self.winfo_screenheight() >= 850:
                self.state("zoomed")
        except tk.TclError:
            pass

    def _configure_dpi_and_fonts(self) -> None:
        try:
            scaling = self.winfo_fpixels("1i") / 72.0
            if 1.0 <= scaling <= 3.5:
                self.tk.call("tk", "scaling", scaling)
        except tk.TclError:
            pass

        fonts = {
            "TkDefaultFont": 11,
            "TkTextFont": 11,
            "TkMenuFont": 11,
            "TkHeadingFont": 11,
            "TkTooltipFont": 10,
            "TkCaptionFont": 11,
            "TkSmallCaptionFont": 10,
            "TkIconFont": 11,
        }
        for name, size in fonts.items():
            try:
                tkfont.nametofont(name).configure(family=FONT_FAMILY, size=size)
            except tk.TclError:
                continue

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", font=(FONT_FAMILY, 11), background=COLORS["bg"], foreground=COLORS["text"])
        style.configure("App.TFrame", background=COLORS["bg"])
        style.configure("LeftPane.TFrame", background=COLORS["left_bg"])
        style.configure("RightPane.TFrame", background=COLORS["right_bg"])
        style.configure("Header.TFrame", background=COLORS["header"], padding=(24, 18))
        style.configure("Card.TFrame", background=COLORS["card"], relief="flat", borderwidth=0)
        style.configure("ActionCard.TFrame", background=COLORS["card_blue"], relief="flat", borderwidth=0)
        style.configure("ModeCard.TFrame", background=COLORS["card_mint"], relief="flat", borderwidth=0)
        style.configure("ReportCard.TFrame", background=COLORS["card_lilac"], relief="flat", borderwidth=0)
        style.configure("LogCard.TFrame", background=COLORS["card_warm"], relief="flat", borderwidth=0)
        style.configure("MetricBlue.TFrame", background=COLORS["blue_soft"], relief="flat", borderwidth=0)
        style.configure("MetricGreen.TFrame", background=COLORS["green_soft"], relief="flat", borderwidth=0)
        style.configure("MetricAmber.TFrame", background=COLORS["amber_soft"], relief="flat", borderwidth=0)
        style.configure("MetricViolet.TFrame", background=COLORS["violet_soft"], relief="flat", borderwidth=0)
        style.configure("HeaderTitle.TLabel", background=COLORS["header"], foreground="#ffffff", font=(FONT_FAMILY, 22, "bold"))
        style.configure("HeaderMuted.TLabel", background=COLORS["header"], foreground="#dbeafe", font=(FONT_FAMILY, 11))
        style.configure("Status.TLabel", background=COLORS["header_2"], foreground="#ffffff", padding=(12, 6), font=(FONT_FAMILY, 11, "bold"))
        style.configure("SectionTitle.TLabel", background=COLORS["card"], foreground=COLORS["text"], font=(FONT_FAMILY, 13, "bold"))
        style.configure("SectionHint.TLabel", background=COLORS["card"], foreground="#475467", font=(FONT_FAMILY, 10))
        style.configure("MetricLabel.TLabel", background=COLORS["card"], foreground="#5b6678", font=(FONT_FAMILY, 10, "bold"))
        style.configure("MetricValue.TLabel", background=COLORS["card"], foreground=COLORS["text"], font=(FONT_FAMILY, 14, "bold"))
        for name, bg in (
            ("Blue", COLORS["blue_soft"]),
            ("Green", COLORS["green_soft"]),
            ("Amber", COLORS["amber_soft"]),
            ("Violet", COLORS["violet_soft"]),
            ("Action", COLORS["card_blue"]),
            ("Mode", COLORS["card_mint"]),
            ("Report", COLORS["card_lilac"]),
            ("Log", COLORS["card_warm"]),
        ):
            style.configure(f"{name}.SectionTitle.TLabel", background=bg, foreground=COLORS["text"], font=(FONT_FAMILY, 13, "bold"))
            style.configure(f"{name}.SectionHint.TLabel", background=bg, foreground="#475467", font=(FONT_FAMILY, 10))
            style.configure(f"{name}.MetricLabel.TLabel", background=bg, foreground="#5b6678", font=(FONT_FAMILY, 10, "bold"))
            style.configure(f"{name}.MetricValue.TLabel", background=bg, foreground=COLORS["text"], font=(FONT_FAMILY, 14, "bold"))
        style.configure("TButton", padding=(12, 8), borderwidth=0, font=(FONT_FAMILY, 11))
        style.configure("Primary.TButton", padding=(14, 10), background=COLORS["accent"], foreground="#ffffff", font=(FONT_FAMILY, 11, "bold"))
        style.map("Primary.TButton", background=[("active", COLORS["accent_hover"]), ("disabled", "#9fb8e8")], foreground=[("disabled", "#eef4ff")])
        style.configure("Secondary.TButton", padding=(12, 9), background="#f7f9fc", foreground=COLORS["text"], bordercolor=COLORS["line"])
        style.map("Secondary.TButton", background=[("active", "#e9eef6"), ("disabled", "#edf2f7")], foreground=[("disabled", "#98a2b3")])
        style.configure("Report.TButton", padding=(10, 8), background=COLORS["accent_soft"], foreground="#1e3a8a")
        style.map("Report.TButton", background=[("active", "#dbeafe")])
        style.configure("TCheckbutton", background=COLORS["card"], foreground=COLORS["text"], font=(FONT_FAMILY, 11))
        style.configure("Treeview", rowheight=36, background="#ffffff", fieldbackground="#ffffff", foreground=COLORS["text"], borderwidth=0, font=(FONT_FAMILY, 11))
        style.configure("Treeview.Heading", background="#e9eff7", foreground="#1f2937", relief="flat", font=(FONT_FAMILY, 11, "bold"))
        style.map("Treeview", background=[("selected", "#dbeafe")], foreground=[("selected", "#0f172a")])

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self, style="Header.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)

        ttk.Label(header, text=APP_TITLE, style="HeaderTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="导入数据、采集市场信号、生成机会判断",
            style="HeaderMuted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.status_label = ttk.Label(header, textvariable=self.status_var, style="Status.TLabel")
        self.status_label.grid(row=0, column=1, sticky="e")

        body = ttk.Frame(self, style="App.TFrame", padding=(22, 18, 22, 22))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, minsize=340)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ttk.Frame(body, style="LeftPane.TFrame", padding=(14, 14))
        right = ttk.Frame(body, style="RightPane.TFrame", padding=(14, 14))
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        right.grid(row=0, column=1, sticky="nsew")

        self._build_controls(left)
        self._build_results(right)

    def _card(
        self,
        parent: ttk.Frame,
        row: int,
        *,
        style_name: str = "Card.TFrame",
        pady: tuple[int, int] = (0, 14),
        weight: int = 0,
    ) -> ttk.Frame:
        if weight:
            parent.rowconfigure(row, weight=weight)
        card = ttk.Frame(parent, style=style_name, padding=(18, 16))
        card.grid(row=row, column=0, sticky="nsew", pady=pady)
        card.columnconfigure(0, weight=1)
        return card

    def _section_header(self, parent: ttk.Frame, title: str, hint: str = "", style_prefix: str = "") -> None:
        title_style = f"{style_prefix}.SectionTitle.TLabel" if style_prefix else "SectionTitle.TLabel"
        hint_style = f"{style_prefix}.SectionHint.TLabel" if style_prefix else "SectionHint.TLabel"
        ttk.Label(parent, text=title, style=title_style).grid(row=0, column=0, sticky="w")
        if hint:
            ttk.Label(parent, text=hint, style=hint_style, wraplength=280).grid(
                row=1, column=0, sticky="w", pady=(3, 12)
            )
        else:
            ttk.Frame(parent, height=8, style=parent.cget("style") or "Card.TFrame").grid(row=1, column=0)

    def _metric_card(
        self,
        parent: ttk.Frame,
        index: int,
        title: str,
        variable: tk.StringVar,
        accent: str,
        style_prefix: str,
    ) -> None:
        row = index // 2
        column = index % 2
        card = ttk.Frame(parent, style=f"Metric{style_prefix}.TFrame", padding=(14, 12))
        card.grid(
            row=row,
            column=column,
            sticky="nsew",
            padx=(0, 12) if column == 0 else (0, 0),
            pady=(0, 12) if row == 0 else (0, 0),
        )
        card.columnconfigure(1, weight=1)
        strip = tk.Frame(card, bg=accent, width=4, height=52, highlightthickness=0)
        strip.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(0, 10))
        ttk.Label(card, text=title, style=f"{style_prefix}.MetricLabel.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Label(card, textvariable=variable, style=f"{style_prefix}.MetricValue.TLabel", wraplength=260).grid(
            row=1, column=1, sticky="w", pady=(6, 0)
        )

    def _build_controls(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(3, weight=1)

        actions = self._card(parent, 0, style_name="ActionCard.TFrame")
        self._section_header(actions, "工作流", "先导入外部数据，再运行完整分析；只改数据时可直接重算报告。", "Action")

        self.import_button = ttk.Button(
            actions,
            text="导入 Excel / CSV 外部数据",
            style="Secondary.TButton",
            command=self.import_external_file,
        )
        self.import_button.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        self.run_button = ttk.Button(
            actions,
            text="运行完整分析",
            style="Primary.TButton",
            command=self.run_full_analysis,
        )
        self.run_button.grid(row=3, column=0, sticky="ew", pady=(0, 10))

        self.reports_button = ttk.Button(
            actions,
            text="只重算报告（不联网）",
            style="Secondary.TButton",
            command=self.rebuild_reports_only,
        )
        self.reports_button.grid(row=4, column=0, sticky="ew", pady=(0, 10))

        self.refresh_button = ttk.Button(actions, text="刷新摘要", style="Secondary.TButton", command=self.refresh_summary)
        self.refresh_button.grid(row=5, column=0, sticky="ew")

        mode = self._card(parent, 1, style_name="ModeCard.TFrame")
        self._section_header(mode, "采集模式", "快速模式会跳过容易限流的 arXiv，其余数据源照常运行。", "Mode")
        ttk.Checkbutton(
            mode,
            text="快速模式：跳过 arXiv（推荐，避免限流卡住）",
            variable=self.fast_mode,
        ).grid(row=2, column=0, sticky="w")

        links = self._card(parent, 2, style_name="ReportCard.TFrame")
        self._section_header(links, "报告入口", style_prefix="Report")
        links.columnconfigure(0, weight=1)
        links.columnconfigure(1, weight=1)
        report_buttons = [
            ("机会排名", ROOT / "reports/opportunity-radar/opportunities.md"),
            ("产品反馈", ROOT / "reports/product-feedback/products.md"),
            ("实时信号", ROOT / "reports/realtime-ai/summary.md"),
            ("项目目录", ROOT),
        ]
        for index, (label, path) in enumerate(report_buttons):
            padx = (0, 8) if index % 2 == 0 else (8, 0)
            ttk.Button(links, text=label, style="Report.TButton", command=lambda p=path: open_path(p)).grid(
                row=2 + index // 2, column=index % 2, sticky="ew", padx=padx, pady=(0, 8)
            )

        log_box = self._card(parent, 3, style_name="LogCard.TFrame", pady=(0, 0), weight=1)
        self._section_header(log_box, "运行日志", style_prefix="Log")
        log_box.columnconfigure(0, weight=1)
        log_box.rowconfigure(2, weight=1)
        self.log_text = tk.Text(
            log_box,
            height=16,
            width=42,
            wrap="word",
            borderwidth=0,
            relief="flat",
            bg=COLORS["console"],
            fg=COLORS["console_text"],
            insertbackground="#93c5fd",
            selectbackground="#334155",
            padx=12,
            pady=10,
            font=(MONO_FONT_FAMILY, 11),
        )
        self.log_text.grid(row=2, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(log_box, orient="vertical", command=self.log_text.yview)
        scroll.grid(row=2, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scroll.set)

    def _build_results(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        metrics = ttk.Frame(parent, style="RightPane.TFrame")
        metrics.grid(row=0, column=0, sticky="ew")
        for column in range(2):
            metrics.columnconfigure(column, weight=1, uniform="metric")
        for row in range(2):
            metrics.rowconfigure(row, weight=1)
        self._metric_card(metrics, 0, "快照", self.snapshot_var, COLORS["accent"], "Blue")
        self._metric_card(metrics, 1, "Top 机会", self.top_var, COLORS["success"], "Green")
        self._metric_card(metrics, 2, "信号规模", self.signals_var, COLORS["warning"], "Amber")
        self._metric_card(metrics, 3, "外部导入", self.external_var, "#7c3aed", "Violet")

        table_box = ttk.Frame(parent, style="Card.TFrame", padding=(18, 16))
        table_box.grid(row=1, column=0, sticky="nsew", pady=(16, 0))
        table_box.columnconfigure(0, weight=1)
        table_box.rowconfigure(2, weight=1)
        ttk.Label(table_box, text="机会排名", style="SectionTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            table_box,
            text="按当前综合评分、付费证据和执行可行性排序",
            style="SectionHint.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(3, 12))

        columns = ("rank", "query", "score", "decision", "evidence")
        self.tree = ttk.Treeview(table_box, columns=columns, show="headings")
        headings = {
            "rank": "排名",
            "query": "方向",
            "score": "分数",
            "decision": "决策层级",
            "evidence": "证据等级",
        }
        widths = {"rank": 58, "query": 210, "score": 72, "decision": 150, "evidence": 150}
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], stretch=column == "query")
        self.tree.tag_configure("odd", background="#f8fafc")
        self.tree.tag_configure("top", background="#ecfeff")
        self.tree.grid(row=2, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(table_box, orient="vertical", command=self.tree.yview)
        scroll.grid(row=2, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)

    def import_external_file(self) -> None:
        path = filedialog.askopenfilename(
            title="选择外部数据文件",
            filetypes=[
                ("Excel/CSV", "*.xlsx *.csv"),
                ("Excel workbook", "*.xlsx"),
                ("CSV", "*.csv"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        self._start_worker(lambda: self._import_external_file(Path(path)))

    def run_full_analysis(self) -> None:
        self._start_worker(lambda: self._run_pipeline(fast=self.fast_mode.get()))

    def rebuild_reports_only(self) -> None:
        self._start_worker(self._rebuild_reports_only)

    def refresh_summary(self) -> None:
        data = read_dashboard_summary()
        self.snapshot_var.set(as_text(data.get("snapshot")) or "暂无")
        self.top_var.set(as_text(data.get("top_opportunity")) or "暂无")
        self.signals_var.set(f"{data.get('search_rows', 0)} 搜索 / {data.get('product_rows', 0)} 产品")
        self.external_var.set(
            f"{data.get('external_rows', 0)} 行 / {quality_label(data.get('external_quality', '暂无'))}"
        )
        self._fill_tree(data.get("opportunities", []))

    def _fill_tree(self, opportunities: list[dict[str, Any]]) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        for index, row in enumerate(opportunities[:20], start=1):
            tags = ("top",) if index <= 3 else ("odd",) if index % 2 else ()
            self.tree.insert(
                "",
                "end",
                values=(
                    row.get("rank") or index,
                    row.get("query", ""),
                    row.get("score", ""),
                    row.get("decision_tier", ""),
                    row.get("evidence_level", ""),
                ),
                tags=tags,
            )

    def _start_worker(self, target: Any) -> None:
        if self.running:
            messagebox.showinfo(APP_TITLE, "当前已有任务在运行。")
            return
        self.running = True
        self._set_controls_enabled(False)
        self.status_var.set("运行中")
        self.worker = threading.Thread(target=self._worker_entry, args=(target,), daemon=True)
        self.worker.start()

    def _worker_entry(self, target: Any) -> None:
        try:
            target()
            self.events.put(("done", None))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def _drain_events(self) -> None:
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "log":
                    self._append_log(str(value))
                elif kind == "done":
                    self.running = False
                    self._set_controls_enabled(True)
                    self.status_var.set("完成")
                    self.refresh_summary()
                elif kind == "error":
                    self.running = False
                    self._set_controls_enabled(True)
                    self.status_var.set("失败")
                    self._append_log(f"\n[ERROR] {value}\n")
                    messagebox.showerror(APP_TITLE, str(value))
        except queue.Empty:
            pass
        self.after(120, self._drain_events)

    def _set_controls_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for button in (self.import_button, self.run_button, self.reports_button, self.refresh_button):
            button.configure(state=state)

    def _append_log(self, text: str) -> None:
        self.log_text.insert("end", text)
        self.log_text.see("end")

    def _log(self, text: str) -> None:
        self.events.put(("log", text if text.endswith("\n") else text + "\n"))

    def _run_command(self, args: list[str], title: str) -> None:
        self._log(f"\n== {title} ==")
        self._log(" ".join(args))
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"
        process = subprocess.Popen(
            args,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        assert process.stdout is not None
        for line in process.stdout:
            self._log(line.rstrip("\n"))
        code = process.wait()
        if code:
            raise RuntimeError(f"{title} 失败，退出码 {code}")

    def _import_external_file(self, path: Path) -> None:
        self._log(f"导入文件：{path}")
        if path.suffix.lower() == ".xlsx":
            summary = import_product_research_xlsx(path)
            self._log(json.dumps(summary, ensure_ascii=False, indent=2))
        elif path.suffix.lower() == ".csv":
            destination = ROOT / "data/external_sources.csv"
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
            self._log(f"已复制到 {destination}")
        else:
            raise RuntimeError("只支持 .xlsx 或 .csv。")
        self._run_command(python_cmd("-B", "scripts/validate_external_sources.py"), "校验外部数据")
        self._run_command(python_cmd("-B", "scripts/import_external_sources.py"), "生成外部导入")

    def _run_pipeline(self, fast: bool) -> None:
        self._run_command(python_cmd("-B", "scripts/check_credentials.py"), "检查账号/API 状态")
        self._run_command(python_cmd("-B", "scripts/validate_external_sources.py"), "校验外部数据")
        self._run_command(python_cmd("-B", "scripts/import_external_sources.py"), "导入外部数据")

        config = "config.realtime-ai-platforms.json"
        if fast:
            config = str(create_fast_config())
            self._log("快速模式已启用：本轮跳过 arXiv。")
        self._run_command(
            python_cmd(
                "-u",
                "-B",
                "scripts/realtime_ai_platform_monitor.py",
                "--once",
                "--config",
                config,
                "--report-out",
                "reports/realtime-ai",
            ),
            "采集实时市场信号",
        )
        self._run_reports()

    def _rebuild_reports_only(self) -> None:
        self._run_command(python_cmd("-B", "scripts/validate_external_sources.py"), "校验外部数据")
        self._run_command(python_cmd("-B", "scripts/import_external_sources.py"), "导入外部数据")
        merge_external_inputs_and_recompute_analysis()
        self._log("已合并外部导入并重算 realtime analysis。")
        self._run_reports(skip_realtime=True)

    def _run_reports(self, skip_realtime: bool = False) -> None:
        self._run_command(
            python_cmd(
                "-B",
                "scripts/generate_product_feedback_report.py",
                "--products",
                "data/products.realtime-ai.csv",
                "--search",
                "data/search_results.realtime-ai.csv",
                "--out",
                "reports/product-feedback",
            ),
            "生成产品反馈报告",
        )
        self._run_command(
            python_cmd(
                "-B",
                "scripts/generate_opportunity_report.py",
                "--analysis",
                "reports/realtime-ai/analysis.json",
                "--out",
                "reports/opportunity-radar",
            ),
            "生成机会排序报告",
        )
        self._run_command(
            python_cmd(
                "-B",
                "scripts/generate_demand_source_report.py",
                "--config",
                "config.product-demand-sources.json",
                "--out",
                "reports/product-demand-sources",
            ),
            "生成需求来源目录",
        )
        if not skip_realtime:
            self._log("完整分析已完成。")


def create_fast_config() -> Path:
    source = ROOT / "config.realtime-ai-platforms.json"
    config = json.loads(source.read_text(encoding="utf-8-sig"))
    collector = config.setdefault("collector", {})
    collector["enabled_sources"] = [
        item for item in collector.get("enabled_sources", []) if item != "arxiv"
    ]
    out = ROOT / "config.realtime-ai-platforms.desktop-fast.json"
    out.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return out.relative_to(ROOT)


def merge_external_inputs_and_recompute_analysis() -> None:
    sys.path.insert(0, str(ROOT))
    from shopping_intel.analysis import analyze
    from shopping_intel.config import load_config
    from shopping_intel.models import Product, SearchResult
    from shopping_intel.report import write_reports

    search_rows = dedupe_rows(
        read_csv_rows(ROOT / "data/search_results.realtime-ai.csv")
        + read_csv_rows(ROOT / "data/search_results.external-imports.csv"),
        ["source", "query", "title", "url", "rank"],
    )
    product_rows = dedupe_rows(
        read_csv_rows(ROOT / "data/products.realtime-ai.csv")
        + read_csv_rows(ROOT / "data/products.external-imports.csv"),
        ["source", "product_id", "title", "url"],
    )
    write_csv(ROOT / "data/search_results.realtime-ai.csv", SEARCH_COLUMNS, search_rows)
    write_csv(ROOT / "data/products.realtime-ai.csv", PRODUCT_COLUMNS, product_rows)

    config = load_config(ROOT / "config.realtime-ai-platforms.json")
    result = analyze(
        config,
        [SearchResult.from_record(row, default_source=row.get("source", "")) for row in search_rows],
        [Product.from_record(row, default_source=row.get("source", "")) for row in product_rows],
        now=datetime.now(timezone.utc),
    )
    write_reports(result, ROOT / "reports/realtime-ai")


def read_dashboard_summary() -> dict[str, Any]:
    opportunities = read_json(ROOT / "reports/opportunity-radar/opportunities.json", [])
    analysis = read_json(ROOT / "reports/realtime-ai/analysis.json", {})
    external_quality = read_json(ROOT / "reports/data-quality/external_sources_quality.json", {})
    external_import = read_json(ROOT / "reports/external-imports/summary.json", {})

    summary = analysis.get("summary") or {}
    top = opportunities[0] if opportunities else {}
    snapshot = ""
    generated_at = analysis.get("generated_at")
    if generated_at:
        snapshot = str(generated_at)[:10]
    return {
        "snapshot": snapshot,
        "top_opportunity": (
            f"{top.get('query')} ({top.get('score')})" if top else ""
        ),
        "search_rows": summary.get("search_result_rows", 0),
        "product_rows": summary.get("product_rows", 0),
        "external_rows": external_import.get("input_rows", 0),
        "external_quality": external_quality.get("status", ""),
        "opportunities": opportunities,
    }


def import_product_research_xlsx(path: Path) -> dict[str, Any]:
    records = read_xlsx_records(path, preferred_sheet="全部数据逐条表达")
    collected_at = datetime.now(timezone.utc).date().isoformat()
    converted: list[dict[str, Any]] = []
    skipped = {"删除": 0, "转表": 0, "other": 0}
    rank_by_query: dict[str, int] = {}

    for raw in records:
        action = as_text(raw.get("action"))
        if action not in KEEP_ACTIONS:
            skipped[action] = skipped.get(action, 0) + 1 if action else skipped.get("other", 0) + 1
            continue
        query = mapped_query(raw)
        rank_by_query[query] = rank_by_query.get(query, 0) + 1
        product_name = as_text(raw.get("product_name"))
        price, currency = parse_price(raw.get("starting_price"))
        review_count = clean_number(raw.get("review_count"))
        rating = clean_number(raw.get("rating"))
        relevance = clean_number(raw.get("relevance_score"))
        source_query = as_text(raw.get("source_query"))
        table_group = as_text(raw.get("table_group")) or as_text(raw.get("segment"))
        description = as_text(raw.get("short_description"))
        processing = as_text(raw.get("processing_explanation"))
        mvp = as_text(raw.get("mvp_opportunity"))

        snippet_parts = [
            query,
            description,
            f"原始关键词: {source_query}" if source_query else "",
            f"分组: {table_group}" if table_group else "",
            f"处理判断: {processing}" if processing else "",
            f"MVP参考: {mvp}" if mvp else "",
        ]
        notes_parts = [
            f"source_workbook={path.name}",
            f"source_evidence={as_text(raw.get('source_evidence'))}",
            f"original_intent={as_text(raw.get('original_intent'))}",
            f"segment={as_text(raw.get('segment'))}",
            f"action={action}",
            f"priority={as_text(raw.get('priority'))}",
            f"target_customer={as_text(raw.get('target_customer'))}",
            f"raw_price={as_text(raw.get('starting_price'))}",
            f"pricing_model={as_text(raw.get('pricing_model'))}",
            "url_is_capterra_search_locator_not_original_product_url",
        ]
        converted.append(
            {
                "record_type": "product",
                "source": "capterra",
                "query": query,
                "title": product_name,
                "url": f"https://www.capterra.com/search/?query={quote_plus(product_name)}"
                if product_name
                else "",
                "rank": rank_by_query[query],
                "result_count": review_count or "1",
                "search_volume": review_count or "",
                "snippet": " | ".join(part for part in snippet_parts if part),
                "product_id": "",
                "price": price,
                "currency": currency,
                "seller": "",
                "category": table_group,
                "stock_status": as_text(raw.get("priority")) or action,
                "rating": rating,
                "review_count": review_count,
                "sales_volume": "",
                "last_updated": collected_at,
                "collected_at": collected_at,
                "signal_type": "b2b_review",
                "buyer_intent_score": "",
                "pain_score": "",
                "source_confidence": "",
                "commercial_relevance": "",
                "metric_name": "review_count" if review_count else "relevance_score",
                "metric_value": review_count or relevance,
                "notes": " | ".join(notes_parts),
            }
        )

    output = ROOT / "data/external_sources.csv"
    write_csv(output, EXTERNAL_COLUMNS, converted)
    report_dir = ROOT / "reports/external-imports"
    report_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_xlsx": str(path),
        "output_csv": str(output),
        "workbook_rows": len(records),
        "imported_rows": len(converted),
        "skipped_rows": skipped,
        "included_actions": sorted(KEEP_ACTIONS),
        "query_counts": {key: rank_by_query[key] for key in sorted(rank_by_query)},
    }
    (report_dir / "product_research_xlsx_import.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def read_xlsx_records(path: Path, preferred_sheet: str) -> list[dict[str, Any]]:
    with zipfile.ZipFile(path) as archive:
        shared_strings = read_shared_strings(archive)
        workbook_root = ET.fromstring(archive.read("xl/workbook.xml"))
        rels_root = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rels = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels_root
            if rel.attrib.get("Id") and rel.attrib.get("Target")
        }
        sheets = workbook_root.findall(
            ".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet"
        )
        selected = None
        for sheet in sheets:
            if sheet.attrib.get("name") == preferred_sheet:
                selected = sheet
                break
        if selected is None:
            selected = sheets[0] if sheets else None
        if selected is None:
            return []
        rel_id = selected.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        target = rels.get(rel_id or "", "")
        if not target:
            return []
        sheet_path = workbook_target_path(target)
        matrix = read_sheet_matrix(archive, sheet_path, shared_strings)
        if not matrix:
            return []
        headers = [as_text(value) for value in matrix[0]]
        return [
            dict(zip(headers, row))
            for row in matrix[1:]
            if any(as_text(value) for value in row)
        ]


def workbook_target_path(target: str) -> str:
    normalized = target.replace("\\", "/").lstrip("/")
    if normalized.startswith("xl/"):
        return normalized
    return f"xl/{normalized}"


def read_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    values: list[str] = []
    for item in root.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"):
        parts = [
            node.text or ""
            for node in item.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
        ]
        values.append("".join(parts))
    return values


def read_sheet_matrix(
    archive: zipfile.ZipFile,
    sheet_path: str,
    shared_strings: list[str],
) -> list[list[Any]]:
    root = ET.fromstring(archive.read(sheet_path))
    rows: list[list[Any]] = []
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    for row_node in root.findall(f".//{ns}row"):
        row_values: list[Any] = []
        for cell in row_node.findall(f"{ns}c"):
            ref = cell.attrib.get("r", "")
            column = column_index(ref)
            while len(row_values) < column:
                row_values.append("")
            row_values[column - 1] = cell_value(cell, shared_strings)
        rows.append(row_values)
    width = max((len(row) for row in rows), default=0)
    for row in rows:
        row.extend([""] * (width - len(row)))
    return rows


def cell_value(cell: ET.Element, shared_strings: list[str]) -> Any:
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    cell_type = cell.attrib.get("t", "")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(f".//{ns}t"))
    value = cell.find(f"{ns}v")
    text = value.text if value is not None else ""
    if cell_type == "s":
        try:
            return shared_strings[int(text)]
        except (ValueError, IndexError):
            return ""
    return text or ""


def column_index(cell_ref: str) -> int:
    match = re.match(r"([A-Z]+)", cell_ref.upper())
    if not match:
        return 1
    result = 0
    for char in match.group(1):
        result = result * 26 + (ord(char) - ord("A") + 1)
    return result


def mapped_query(row: dict[str, Any]) -> str:
    segment = as_text(row.get("segment"))
    source_query = as_text(row.get("source_query"))
    text = " | ".join(
        as_text(row.get(key))
        for key in (
            "source_query",
            "original_intent",
            "segment",
            "product_name",
            "short_description",
            "priority",
            "target_customer",
            "table_group",
            "processing_explanation",
            "mvp_opportunity",
        )
    )
    if contains_any(text, PRODUCT_DATA_TERMS) or segment == "small_business_product_data" or source_query == "catalog management":
        return "ai data entry"
    if segment == "ai_invoice_processing" or contains_any(text, INVOICE_TERMS):
        return "ai invoice processing"
    if contains_any(text, EMAIL_DOC_TERMS):
        return "ai document processing"
    if contains_any(text, ("web scraping", "网页采集", "爬取", "scraping")):
        return "ai web research"
    if contains_any(text, ("lead", "contact", "线索", "获客", "crm")):
        return "ai lead generation"
    if contains_any(text, ("recruit", "hr", "招聘")):
        return "ai recruiting assistant"
    if contains_any(text, ("contract", "legal", "合同", "法律")):
        return "ai contract review"
    if contains_any(text, ("bookkeeping", "accounting", "会计", "记账", "费用", "expense")):
        return "ai bookkeeping"
    if segment == "small_business_document_processing":
        return "ai document processing"
    return "ai document processing"


def parse_price(value: Any) -> tuple[str, str]:
    text = as_text(value)
    if not text:
        return "", ""
    currency = ""
    if "$" in text:
        currency = "USD"
    elif "€" in text:
        currency = "EUR"
    elif "£" in text:
        currency = "GBP"
    elif "¥" in text or "￥" in text:
        currency = "CNY"
    match = re.search(r"[-+]?\d+(?:[.,]\d+)?", text)
    return (match.group(0).replace(",", ""), currency) if match else ("", currency)


def clean_number(value: Any) -> str:
    text = as_text(value).replace(",", "")
    if not text:
        return ""
    try:
        number = float(text)
    except ValueError:
        return ""
    return str(int(number)) if number.is_integer() else str(number)


def contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lowered = f" {text.lower()} "
    return any(term.lower() in lowered for term in terms)


def quality_label(value: Any) -> str:
    labels = {
        "ok": "良好",
        "needs_review": "待复核",
        "error": "异常",
        "missing": "缺失",
    }
    text = as_text(value)
    return labels.get(text, text or "暂无")


def as_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return fallback


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def dedupe_rows(rows: list[dict[str, str]], keys: list[str]) -> list[dict[str, str]]:
    seen: set[tuple[str, ...]] = set()
    result: list[dict[str, str]] = []
    for row in rows:
        signature = tuple(str(row.get(key, "")).strip().lower() for key in keys)
        if signature in seen:
            continue
        seen.add(signature)
        result.append(row)
    return result


def open_path(path: Path) -> None:
    if not path.exists():
        messagebox.showwarning(APP_TITLE, f"文件不存在：\n{path}")
        return
    os.startfile(str(path))


if __name__ == "__main__":
    raise SystemExit(main())
