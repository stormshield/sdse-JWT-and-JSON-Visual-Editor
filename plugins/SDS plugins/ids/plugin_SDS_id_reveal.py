
import tkinter as tk
import json
import os
import sys
import base64
import ctypes

def get_plugin_resource_path(relative_path):
    """Get absolute path to plugin resource, works for dev and for PyInstaller."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dev_path = os.path.join(current_dir, relative_path)
    
    if os.path.exists(dev_path):
        return dev_path
    
    try:
        base_path = sys._MEIPASS
        possible_paths = [
            os.path.join(base_path, "plugins", "SDS plugins", "ids", relative_path),
            os.path.join(base_path, "plugins", "SDS_plugins", "ids", relative_path),
            os.path.join(base_path, relative_path)
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return possible_paths[0]
    except Exception:
        return dev_path

# Load translations
try:
    lang_path = get_plugin_resource_path("languages_reveal.json")
    if os.path.exists(lang_path):
        with open(lang_path, "r", encoding="utf-8") as f:
            translations = json.load(f)
    else:
        translations = {}
except Exception as e:
    print(f"Plugin ID Reveal: Could not load languages_reveal.json: {e}")
    translations = {}

# Try to import cryptography for certificate CN extraction
try:
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    from cryptography.x509.oid import NameOID
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    x509 = None
    default_backend = None
    NameOID = None

# Windows API constants for physical key state detection
VK_RMENU = 0xA5  # Virtual key code for Right Alt (AltGr)


class Plugin:
    def __init__(self, app):
        self.app = app
        self.translations = translations
        self._is_revealing = False
        self._original_text = None
        self._original_insert_pos = None
        self._original_yview = None
        self._id_name_map = {}  # maps id -> display name
        self._poll_timer = None

    def t(self, key, **kwargs):
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
            except:
                return text
        return text

    def register(self):
        """Bind AltGr detection using Windows API for reliable detection."""
        # On Windows, AltGr is translated by the keyboard driver to Ctrl+Alt.
        # Tkinter never sees an Alt_R keysym, only Control_L with a modified state.
        # Solution: use ctypes to call GetAsyncKeyState(VK_RMENU) to check the
        # physical state of the right Alt key, and poll for its release.
        
        self.app.bind_all("<KeyPress>", self._on_any_keypress, add="+")

    def _is_altgr_physically_pressed(self):
        """Check if AltGr (Right Alt) is physically pressed using Windows API."""
        try:
            return bool(ctypes.windll.user32.GetAsyncKeyState(VK_RMENU) & 0x8000)
        except Exception:
            return False

    def _on_any_keypress(self, event):
        """Detect AltGr press via any key event + physical key state check."""
        if self._is_revealing:
            return
        
        # Check if AltGr is physically pressed right now
        if self._is_altgr_physically_pressed():
            self._on_altgr_press()

    def _start_release_poll(self):
        """Poll every 50ms to detect when AltGr is released."""
        if not self._is_revealing:
            return
        
        if not self._is_altgr_physically_pressed():
            # AltGr was released — restore original text
            self._on_altgr_release()
            return
        
        # Still held — check again in 50ms
        self._poll_timer = self.app.after(50, self._start_release_poll)

    def _on_altgr_press(self, event=None):
        """When AltGr is pressed, replace IDs with their names/CN in the text widget."""
        if self._is_revealing:
            return  # Already revealing, don't re-trigger
        
        # Get current text
        full_text = self.app.text.get("1.0", "end-1c")
        if not full_text.strip():
            return
        
        # Try to parse as JSON
        try:
            data = json.loads(full_text)
        except json.JSONDecodeError:
            return
        
        # Build ID -> name/CN mapping
        self._id_name_map = self._build_id_map(data)
        
        if not self._id_name_map:
            return  # No mappable IDs found
        
        # Check if any IDs actually appear in the text
        has_match = False
        for id_val in self._id_name_map:
            if id_val in full_text:
                has_match = True
                break
        
        if not has_match:
            return
        
        # Save original state
        self._original_text = full_text
        self._original_insert_pos = self.app.text.index("insert")
        self._original_yview = self.app.text.yview()
        self._is_revealing = True
        
        # Replace IDs with names in the text
        modified_text = full_text
        for id_val, display_name in self._id_name_map.items():
            # We wrap the display name with markers so it's visually distinct
            # Use the format: «name» to make it clear it's a resolved name
            replacement = display_name
            modified_text = modified_text.replace(id_val, replacement)
        
        # Update the text widget (without triggering undo)
        self.app.text.config(state="normal")
        
        # Disable undo tracking during reveal
        try:
            self.app.text.edit_separator()
        except Exception:
            pass
        
        self.app.text.delete("1.0", "end")
        self.app.text.insert("1.0", modified_text)
        
        # Make text read-only during reveal to prevent edits on modified content
        self.app.text.config(state="disabled")
        
        # Restore scroll position
        try:
            if self._original_yview:
                self.app.text.yview_moveto(self._original_yview[0])
        except Exception:
            pass
        
        # Start polling for AltGr release — MUST run even if highlighting fails
        try:
            # Apply syntax highlighting on the modified text
            try:
                self.app.apply_syntax_highlighting()
            except Exception:
                pass
            
            # Apply special tag to the revealed names so they stand out
            self._highlight_revealed_names()
            
            # Update status bar
            try:
                count = sum(1 for id_val in self._id_name_map if id_val in self._original_text)
                self.app.status.set(self.t("status_revealing", count=count))
            except Exception:
                pass
        finally:
            # Always start polling so we can restore on release
            self._start_release_poll()

    def _on_altgr_release(self, event=None):
        """When AltGr is released, restore the original text."""
        if not self._is_revealing:
            return
        
        # Cancel any pending poll timer
        if self._poll_timer is not None:
            try:
                self.app.after_cancel(self._poll_timer)
            except Exception:
                pass
            self._poll_timer = None
        
        if self._original_text is None:
            self._is_revealing = False
            return
        
        # Re-enable editing
        self.app.text.config(state="normal")
        
        # Restore original text
        self.app.text.delete("1.0", "end")
        self.app.text.insert("1.0", self._original_text)
        
        # Restore cursor and scroll position
        try:
            if self._original_insert_pos:
                self.app.text.mark_set("insert", self._original_insert_pos)
        except Exception:
            pass
        
        try:
            if self._original_yview:
                self.app.text.yview_moveto(self._original_yview[0])
        except Exception:
            pass
        
        # Reset undo to avoid the reveal/restore being in undo history
        try:
            self.app.text.edit_reset()
        except Exception:
            pass
        
        # Re-apply syntax highlighting
        try:
            self.app.apply_syntax_highlighting()
        except Exception:
            pass
        
        # Restore status bar
        try:
            self.app.status.set(self.t("status_restored"))
        except Exception:
            pass
        
        # Reset state
        self._is_revealing = False
        self._original_text = None
        self._original_insert_pos = None
        self._original_yview = None

    def _build_id_map(self, data):
        """
        Build a mapping of ID -> display name from the JSON data.
        Looks at:
        - certificateData: id -> CN from certificate (or subject string)
        - ldapData: id -> configuration.name
        """
        id_map = {}
        
        # Process certificateData
        cert_data_list = data.get("certificateData", [])
        if isinstance(cert_data_list, list):
            for entry in cert_data_list:
                if not isinstance(entry, dict):
                    continue
                cert_id = entry.get("id", "")
                if not cert_id:
                    continue
                
                # Try to extract CN from certificate
                display_name = self._extract_cert_cn(entry)
                if display_name:
                    id_map[cert_id] = display_name
        
        # Process ldapData
        ldap_data_list = data.get("ldapData", [])
        if isinstance(ldap_data_list, list):
            for entry in ldap_data_list:
                if not isinstance(entry, dict):
                    continue
                ldap_id = entry.get("id", "")
                if not ldap_id:
                    continue
                
                # Get name from configuration
                config = entry.get("configuration", {})
                name = config.get("name", "")
                if name:
                    id_map[ldap_id] = name
                else:
                    # Fallback: use address if available
                    access = config.get("access", {})
                    addr = access.get("address", "")
                    if addr:
                        id_map[ldap_id] = f"LDAP: {addr}"
        
        return id_map

    def _extract_cert_cn(self, cert_entry):
        """Extract CN (Common Name) from a certificate entry's base64 data."""
        cert_b64 = cert_entry.get("data", "")
        if not cert_b64:
            return None
        
        if not HAS_CRYPTO:
            # Without cryptography library, we can't parse the cert
            return None
        
        try:
            der_bytes = base64.b64decode(cert_b64, validate=True)
            cert_obj = x509.load_der_x509_certificate(der_bytes, default_backend())
            
            # Try to get CN from subject
            cn_attrs = cert_obj.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
            if cn_attrs:
                return cn_attrs[0].value
            
            # Fallback to full subject
            return cert_obj.subject.rfc4514_string()
        except Exception:
            return None

    def _highlight_revealed_names(self):
        """Apply visual highlighting to all revealed display names."""
        tag_name = "id_reveal"
        self.app.text.tag_remove(tag_name, "1.0", "end")
        
        # Get current font info to build a bold variant
        try:
            current_font = self.app.text.cget("font")
            from tkinter import font as tkfont
            f = tkfont.Font(font=current_font)
            bold_font = (f.actual("family"), f.actual("size"), "bold")
        except Exception:
            bold_font = ("TkFixedFont", 11, "bold")
        
        # Configure the tag with a distinct style
        self.app.text.tag_configure(
            tag_name,
            background="#2d2d2d",
            foreground="#00e5ff",
            font=bold_font
        )
        
        # Find and tag all occurrences of each display name
        for display_name in self._id_name_map.values():
            start_pos = "1.0"
            while True:
                pos = self.app.text.search(display_name, start_pos, stopindex="end", nocase=False)
                if not pos:
                    break
                end_pos = f"{pos}+{len(display_name)}c"
                self.app.text.tag_add(tag_name, pos, end_pos)
                start_pos = end_pos
        
        # Raise this tag above others for visibility
        self.app.text.tag_raise(tag_name)

