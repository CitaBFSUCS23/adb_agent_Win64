import tkinter as tk
from tkinter import ttk
from gui.i18n import tr, set_lang, get_lang, available_langs
from gui.config import NAV_PAGES


class LanguageAndNavWidget:

    def __init__(self, parent, on_lang_changed=None, on_nav_clicked=None):
        self.frame = ttk.Frame(parent)
        self.on_lang_changed = on_lang_changed
        self.on_nav_clicked = on_nav_clicked

        self._build_widgets()

    def _build_widgets(self):
        # One row: language selector and navigation buttons together
        single_row = ttk.Frame(self.frame)
        single_row.pack(fill="x", padx=5, pady=5)

        self.lbl_lang = ttk.Label(single_row, text="")
        self.lbl_lang.pack(side="left", padx=2)
        
        self.lang_combo = ttk.Combobox(single_row, values=available_langs(), state="readonly", width=10)
        self.lang_combo.set(get_lang())
        self.lang_combo.pack(side="left", padx=2)
        self.lang_combo.bind("<<ComboboxSelected>>", self._on_lang_changed_event)

        # Navigation buttons
        self.nav_buttons = []
        for i, (_, page_key) in enumerate(NAV_PAGES):
            btn = ttk.Button(single_row, text="", width=8,
                           command=lambda idx=i: self._on_nav_clicked_event(idx))
            btn.pack(side="left", padx=1)
            self.nav_buttons.append(btn)

    def _on_lang_changed_event(self, event=None):
        if new_lang := self.lang_combo.get():
            set_lang(new_lang)
            if self.on_lang_changed:
                self.on_lang_changed()

    def _on_nav_clicked_event(self, index):
        if self.on_nav_clicked:
            self.on_nav_clicked(index)

    def refresh_ui(self):
        self.lbl_lang.config(text=tr("main_language_label"))
        for i, btn in enumerate(self.nav_buttons):
            btn.config(text=tr(NAV_PAGES[i][1]))
