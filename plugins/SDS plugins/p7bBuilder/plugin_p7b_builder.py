import os
import json
import sys
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable, List

# Optional drag & drop support (works when the app uses TkinterDnD.Tk)
try:
    from tkinterdnd2 import DND_FILES  # type: ignore
    HAS_DND = True
except Exception:
    DND_FILES = None
    HAS_DND = False

MISSING_DEPS = []

try:
    from cryptography import x509
    from cryptography.hazmat.primitives.serialization import Encoding
    from cryptography.hazmat.primitives.serialization import pkcs7
except Exception:
    x509 = None
    Encoding = None
    pkcs7 = None
    MISSING_DEPS.append("cryptography")


def get_plugin_resource_path(relative_path: str) -> str:
    """Get absolute path to plugin resource, works for dev and for PyInstaller."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dev_path = os.path.join(current_dir, relative_path)

    if os.path.exists(dev_path):
        return dev_path

    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
        possible_paths = [
            os.path.join(base_path, "plugins", "SDS plugins", "p7bBuilder", relative_path),
            os.path.join(base_path, "plugins", "SDS_plugins", "p7bBuilder", relative_path),
            os.path.join(base_path, relative_path),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return possible_paths[0]
    except Exception:
        return dev_path


def _load_translations() -> dict:
    try:
        lang_path = get_plugin_resource_path("languages.json")
        if os.path.exists(lang_path):
            with open(lang_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Plugin SDS P7B Builder: Could not load languages.json: {e}")
        traceback.print_exc()
    return {}


def _split_dnd_files(data: str) -> List[str]:
    """Parse TkinterDnD's event.data for DND_FILES into a list of paths."""
    if not data:
        return []

    data = data.strip()

    # Common format on Windows: {C:\Path With Spaces\a.cer} {C:\b.cer}
    if "{" in data and "}" in data:
        out: List[str] = []
        current = []
        in_brace = False
        for ch in data:
            if ch == "{":
                in_brace = True
                current = []
                continue
            if ch == "}":
                in_brace = False
                token = "".join(current).strip()
                if token:
                    out.append(token)
                current = []
                continue
            if in_brace:
                current.append(ch)
        return [_normalize_path(p) for p in out if p]

    # Fallback: split on whitespace
    parts = [p for p in data.split() if p]
    return [_normalize_path(p) for p in parts]


def _normalize_path(path: str) -> str:
    p = path.strip().strip('"')
    # TkDND often uses forward slashes
    p = p.replace("/", os.sep)
    return os.path.normpath(p)


def _load_x509_certificate_from_file(path: str):
    if x509 is None:
        raise RuntimeError("cryptography is required to load certificates")

    with open(path, "rb") as f:
        raw = f.read()

    if b"-----BEGIN" in raw[:4096]:
        return x509.load_pem_x509_certificate(raw)
    return x509.load_der_x509_certificate(raw)


def _try_enable_dnd(widget, handler: Callable) -> bool:
    """Enable TkinterDnD drop on a widget if supported (runtime check)."""
    if not HAS_DND or DND_FILES is None:
        return False

    try:
        drop_target_register = getattr(widget, "drop_target_register", None)
        dnd_bind = getattr(widget, "dnd_bind", None)
        if callable(drop_target_register) and callable(dnd_bind):
            drop_target_register(DND_FILES)
            dnd_bind("<<Drop>>", handler)
            return True
    except Exception:
        pass
    return False


class Plugin:
    def __init__(self, app):
        self.app = app
        self.translations = _load_translations()
        self.current_menu_label = None
        self.window = None
        self.keep_on_top_var = None
        self.keep_on_top_job = None

        print("Plugin SDS P7B Builder: Loaded")

    def t(self, key: str, **kwargs):
        lang = getattr(self.app, "current_language", "en")
        try:
            settings_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "settings.json")
            if os.path.exists(settings_path):
                with open(settings_path, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                lang = settings.get("language", lang)
        except Exception:
            pass

        text = self.translations.get(lang, self.translations.get("en", {})).get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:
                return text
        return text

    def register(self):
        pass

    def on_event(self, event_name, data):
        if event_name == "ui_ready":
            self.register_menu()
        elif event_name == "language_changed":
            self.update_menu_language()

    def register_menu(self):
        try:
            tools_menu = self.app.tools_menu
            tools_menu.add_separator()
            label = self.t("menu_p7b_builder")
            self.current_menu_label = label
            tools_menu.add_command(label=label, command=self.open_window)
            print("Plugin SDS P7B Builder: Added to menu")
        except Exception as e:
            print(f"Plugin SDS P7B Builder: Error registering menu: {e}")
            traceback.print_exc()

    def update_menu_language(self):
        if self.current_menu_label is None:
            return

        try:
            tools_menu = self.app.tools_menu
            new_label = self.t("menu_p7b_builder")
            if new_label == self.current_menu_label:
                return

            last_index = tools_menu.index('end')
            if last_index is None:
                return

            for i in range(last_index + 1):
                try:
                    item_label = tools_menu.entrycget(i, "label")
                    if item_label == self.current_menu_label:
                        tools_menu.entryconfig(i, label=new_label)
                        self.current_menu_label = new_label
                        break
                except Exception:
                    continue
        except Exception as e:
            print(f"Plugin SDS P7B Builder: Error updating menu language: {e}")

    def open_window(self):
        if MISSING_DEPS:
            messagebox.showerror(
                self.t("missing_deps_title"),
                self.t("missing_deps_text", deps=", ".join(MISSING_DEPS)),
            )
            return

        if self.window is not None and self.window.winfo_exists():
            self.window.lift()
            return

        self.window = tk.Toplevel(self.app)
        self.window.title(self.t("window_title"))

        # Default: not topmost (user can enable via checkbox)
        self.keep_on_top_var = tk.BooleanVar(master=self.window, value=False)

        # Center the window relative to the main app (or screen)
        win_w, win_h = 720, 480
        try:
            self._center_window(self.window, win_w, win_h)
        except Exception:
            # Fallback to simple geometry if centering fails
            self.window.geometry(f"{win_w}x{win_h}")

        # Ensure it's raised and focused
        try:
            self.window.lift()
            self.window.focus_force()
        except Exception:
            pass

        root = ttk.Frame(self.window, padding=12)
        root.pack(fill="both", expand=True)

        top = ttk.Frame(root)
        top.pack(fill="x")

        top_row = ttk.Frame(top)
        top_row.pack(fill="x")

        info = ttk.Label(top_row, text=self.t("intro"), justify="left")
        info.pack(side="left", anchor="w", fill="x", expand=True)

        keep_on_top_cb = ttk.Checkbutton(
            top_row,
            text=self.t("keep_on_top"),
            variable=self.keep_on_top_var,
            command=self._on_keep_on_top_changed,
        )
        keep_on_top_cb.pack(side="right", anchor="ne")

        if not HAS_DND:
            warn = ttk.Label(top, text=self.t("dnd_unavailable"), foreground="#a94442")
            warn.pack(anchor="w", pady=(6, 0))

        mid = ttk.Frame(root)
        mid.pack(fill="both", expand=True, pady=(10, 10))

        left = ttk.Frame(mid)
        left.pack(side="left", fill="both", expand=True)

        ttk.Label(left, text=self.t("cert_list_label")).pack(anchor="w")

        list_frame = ttk.Frame(left)
        list_frame.pack(fill="both", expand=True)

        self.cert_list = tk.Listbox(list_frame, selectmode=tk.EXTENDED)
        self.cert_list.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.cert_list.yview)
        scrollbar.pack(side="right", fill="y")
        self.cert_list.configure(yscrollcommand=scrollbar.set)

        drop_area = ttk.Label(left, text=self.t("drop_area"), anchor="center")
        drop_area.pack(fill="x", pady=(8, 0))

        # Drag & drop registration (works if the main root is TkinterDnD.Tk)
        _try_enable_dnd(drop_area, self._on_drop_files)
        _try_enable_dnd(self.cert_list, self._on_drop_files)

        right = ttk.Frame(mid)
        right.pack(side="right", fill="y", padx=(12, 0))

        ttk.Button(right, text=self.t("btn_add"), command=self._add_files_dialog).pack(fill="x")
        ttk.Button(right, text=self.t("btn_remove"), command=self._remove_selected).pack(fill="x", pady=(6, 0))
        ttk.Button(right, text=self.t("btn_clear"), command=self._clear).pack(fill="x", pady=(6, 0))

        out = ttk.LabelFrame(root, text=self.t("output_group"), padding=10)
        out.pack(fill="x")

        self.output_path_var = tk.StringVar(value="")
        out_row = ttk.Frame(out)
        out_row.pack(fill="x")

        ttk.Label(out_row, text=self.t("output_path_label")).pack(side="left")
        ttk.Entry(out_row, textvariable=self.output_path_var).pack(side="left", fill="x", expand=True, padx=(8, 8))
        ttk.Button(out_row, text=self.t("btn_browse"), command=self._browse_output).pack(side="left")

        fmt_row = ttk.Frame(out)
        fmt_row.pack(fill="x", pady=(8, 0))

        ttk.Label(fmt_row, text=self.t("output_format_label")).pack(side="left")
        self.format_var = tk.StringVar(value="DER")
        ttk.Radiobutton(fmt_row, text=self.t("format_der"), value="DER", variable=self.format_var).pack(side="left", padx=(8, 0))
        ttk.Radiobutton(fmt_row, text=self.t("format_pem"), value="PEM", variable=self.format_var).pack(side="left", padx=(8, 0))

        bottom = ttk.Frame(root)
        bottom.pack(fill="x", pady=(10, 0))

        ttk.Button(bottom, text=self.t("btn_generate"), command=self._generate_p7b).pack(side="right")

    def _on_keep_on_top_changed(self):
        try:
            enabled = bool(self.keep_on_top_var.get()) if self.keep_on_top_var is not None else False
        except Exception:
            enabled = False
        self._apply_topmost(enabled)

    def _apply_topmost(self, enabled: bool):
        if self.window is None:
            return
        try:
            if not self.window.winfo_exists():
                return
        except Exception:
            return

        # Cancel any previous keep-on-top loop
        if self.keep_on_top_job is not None:
            try:
                self.window.after_cancel(self.keep_on_top_job)
            except Exception:
                pass
            self.keep_on_top_job = None

        # Ensure window is fully initialized before applying attributes
        try:
            self.window.update_idletasks()
        except Exception:
            pass

        try:
            # Make sure window is visible before toggling topmost
            if enabled:
                try:
                    self.window.deiconify()
                except Exception:
                    pass
            self.window.attributes("-topmost", bool(enabled))
            # Force immediate update
            self.window.update()
        except Exception as e:
            print(f"Error setting topmost: {e}")

        if enabled:
            try:
                self.window.lift()
                self.window.focus_force()
            except Exception:
                pass
            # Keep reinforcing topmost in case the WM drops it
            self.keep_on_top_job = self.window.after(500, self._keep_on_top_tick)

    def _keep_on_top_tick(self):
        if self.window is None or self.keep_on_top_var is None:
            return
        try:
            if not self.window.winfo_exists():
                return
        except Exception:
            return

        try:
            if self.keep_on_top_var.get():
                self.window.attributes("-topmost", True)
                self.window.lift()
                self.keep_on_top_job = self.window.after(500, self._keep_on_top_tick)
            else:
                self.keep_on_top_job = None
        except Exception:
            self.keep_on_top_job = None

    def _center_window(self, win, width, height):
        """Center a Toplevel window relative to the main app window if possible."""
        win.update_idletasks()
        try:
            parent = self.app
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()

            x = px + max(0, (pw - width) // 2)
            y = py + max(0, (ph - height) // 2)
        except Exception:
            sw = win.winfo_screenwidth()
            sh = win.winfo_screenheight()
            x = max(0, (sw - width) // 2)
            y = max(0, (sh - height) // 2)

        win.geometry(f"{width}x{height}+{x}+{y}")

    def _on_drop_files(self, event):
        try:
            paths = _split_dnd_files(getattr(event, "data", ""))
            self._add_files(paths)
        except Exception as e:
            messagebox.showerror(self.t("error_title"), f"{e}")

    def _add_files_dialog(self):
        file_types = [
            (self.t("filetype_certs"), "*.cer;*.crt;*.pem;*.der"),
            (self.t("filetype_all"), "*.*"),
        ]

        paths = filedialog.askopenfilenames(title=self.t("dialog_add_title"), filetypes=file_types)
        if not paths:
            return
        self._add_files(list(paths))

    def _add_files(self, paths: List[str]):
        if not paths:
            return

        existing = set(self.cert_list.get(0, tk.END))
        for p in paths:
            p = _normalize_path(p)
            if not p:
                continue
            if not os.path.isfile(p):
                continue
            ext = os.path.splitext(p)[1].lower()
            if ext not in (".cer", ".crt", ".pem", ".der"):
                continue
            if p in existing:
                continue
            self.cert_list.insert(tk.END, p)
            existing.add(p)

    def _remove_selected(self):
        sel = list(self.cert_list.curselection())
        if not sel:
            return
        for idx in reversed(sel):
            self.cert_list.delete(idx)

    def _clear(self):
        self.cert_list.delete(0, tk.END)

    def _browse_output(self):
        default_ext = ".p7b" if self.format_var.get() == "DER" else ".p7b"
        filetypes = [
            (self.t("filetype_p7b"), "*.p7b;*.p7c"),
            (self.t("filetype_all"), "*.*"),
        ]

        path = filedialog.asksaveasfilename(
            title=self.t("dialog_save_title"),
            defaultextension=default_ext,
            filetypes=filetypes,
        )
        if not path:
            return
        self.output_path_var.set(path)

    def _generate_p7b(self):
        cert_paths = list(self.cert_list.get(0, tk.END))
        if not cert_paths:
            messagebox.showwarning(self.t("warn_title"), self.t("warn_no_certs"))
            return

        output_path = (self.output_path_var.get() or "").strip()
        if not output_path:
            messagebox.showwarning(self.t("warn_title"), self.t("warn_no_output"))
            return

        if x509 is None or pkcs7 is None or Encoding is None:
            messagebox.showerror(self.t("missing_deps_title"), self.t("missing_deps_text", deps="cryptography"))
            return

        try:
            certs = []
            for p in cert_paths:
                certs.append(_load_x509_certificate_from_file(p))

            encoding = Encoding.DER if self.format_var.get() == "DER" else Encoding.PEM

            # cryptography exposes serialize_certificates for degenerate PKCS7 (certs only)
            try:
                p7b_bytes = pkcs7.serialize_certificates(certs, encoding)
            except TypeError:
                # Some versions have keyword-only encoding
                p7b_bytes = pkcs7.serialize_certificates(certs, encoding=encoding)

            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(p7b_bytes)

            messagebox.showinfo(self.t("success_title"), self.t("success_text", path=output_path))

        except Exception as e:
            traceback.print_exc()
            messagebox.showerror(self.t("error_title"), f"{e}")
