
import tkinter as tk

class Plugin:
    def __init__(self, app):
        self.app = app

    def register(self):
        pass

    def extend_context_menu(self, menu, event):
        index = self.app.text.index(f"@{event.x},{event.y}")
        try:
            token = self.app.text.get(f"{index} wordstart", f"{index} wordend").strip().lower()
        except Exception:
            token = ""
            
        if token in ("true", "false"):
            start_idx = self.app.text.index(f"{index} wordstart")
            end_idx = self.app.text.index(f"{index} wordend")
            new_val = "false" if token == "true" else "true"
            menu.add_command(label=new_val,
                             command=lambda s=start_idx, e=end_idx, v=new_val: self.app.replace_word(s, e, v))
