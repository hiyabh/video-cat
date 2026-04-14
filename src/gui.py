"""GUI interface for VideoCat using CustomTkinter."""

import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from .config import Config, FORMAT_PRESETS, SUPPORTED_VIDEO_EXTENSIONS
from .pipeline import run_pipeline
from .video_processor import ProcessingOptions


class VideoCatApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("VideoCat — Video to Viral Clips")
        self.geometry("700x750")
        self.resizable(False, False)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.config = Config()
        self._is_processing = False
        self._build_ui()

    def _build_ui(self):
        # Header
        header = ctk.CTkLabel(
            self, text="VideoCat", font=ctk.CTkFont(size=28, weight="bold"),
        )
        header.pack(pady=(20, 5))

        subtitle = ctk.CTkLabel(
            self, text="Turn long videos into short viral clips",
            font=ctk.CTkFont(size=14), text_color="gray",
        )
        subtitle.pack(pady=(0, 20))

        # Input file
        input_frame = ctk.CTkFrame(self)
        input_frame.pack(fill="x", padx=30, pady=5)

        ctk.CTkLabel(input_frame, text="Video File:").pack(side="left", padx=10)
        self.input_entry = ctk.CTkEntry(input_frame, width=400)
        self.input_entry.pack(side="left", padx=5, expand=True, fill="x")
        ctk.CTkButton(
            input_frame, text="Browse", width=80, command=self._browse_video,
        ).pack(side="right", padx=10)

        # Format selection
        format_frame = ctk.CTkFrame(self)
        format_frame.pack(fill="x", padx=30, pady=5)

        ctk.CTkLabel(format_frame, text="Format:").pack(side="left", padx=10)
        self.format_var = ctk.StringVar(value="vertical")
        for key, preset in FORMAT_PRESETS.items():
            ctk.CTkRadioButton(
                format_frame, text=preset["label"],
                variable=self.format_var, value=key,
            ).pack(side="left", padx=10)

        # Settings
        settings_frame = ctk.CTkFrame(self)
        settings_frame.pack(fill="x", padx=30, pady=5)

        # Max clips
        ctk.CTkLabel(settings_frame, text="Max Clips:").grid(row=0, column=0, padx=10, pady=8, sticky="w")
        self.clips_slider = ctk.CTkSlider(settings_frame, from_=1, to=10, number_of_steps=9, width=200)
        self.clips_slider.set(self.config.max_clips)
        self.clips_slider.grid(row=0, column=1, padx=5, pady=8)
        self.clips_label = ctk.CTkLabel(settings_frame, text=str(self.config.max_clips))
        self.clips_label.grid(row=0, column=2, padx=5)
        self.clips_slider.configure(command=lambda v: self.clips_label.configure(text=str(int(v))))

        # Language
        ctk.CTkLabel(settings_frame, text="Language:").grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.lang_var = ctk.StringVar(value="auto")
        lang_menu = ctk.CTkOptionMenu(
            settings_frame, variable=self.lang_var,
            values=["auto", "he", "en", "ar", "es", "fr"],
        )
        lang_menu.grid(row=1, column=1, padx=5, pady=8, sticky="w")

        # Whisper model
        ctk.CTkLabel(settings_frame, text="Model:").grid(row=2, column=0, padx=10, pady=8, sticky="w")
        self.model_var = ctk.StringVar(value=self.config.whisper_model)
        model_menu = ctk.CTkOptionMenu(
            settings_frame, variable=self.model_var,
            values=["tiny", "base", "small", "medium", "large-v3"],
        )
        model_menu.grid(row=2, column=1, padx=5, pady=8, sticky="w")

        # Optional: music, logo, font
        extras_frame = ctk.CTkFrame(self)
        extras_frame.pack(fill="x", padx=30, pady=5)

        self.music_path = self._file_row(extras_frame, "Music:", 0, self._browse_music)
        self.logo_path = self._file_row(extras_frame, "Logo:", 1, self._browse_logo)
        self.font_path = self._file_row(extras_frame, "Font:", 2, self._browse_font)

        # Word animation toggle
        self.animate_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            extras_frame, text="Word-by-word subtitle animation",
            variable=self.animate_var,
        ).grid(row=3, column=0, columnspan=3, padx=10, pady=8, sticky="w")

        # Process button
        self.process_btn = ctk.CTkButton(
            self, text="Create Clips", height=45,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self._start_processing,
        )
        self.process_btn.pack(pady=20)

        # Progress
        self.progress_bar = ctk.CTkProgressBar(self, width=500)
        self.progress_bar.pack(pady=5)
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(
            self, text="Ready", font=ctk.CTkFont(size=13), text_color="gray",
        )
        self.status_label.pack(pady=5)

        # Log area
        self.log_text = ctk.CTkTextbox(self, height=120, width=620)
        self.log_text.pack(padx=30, pady=(5, 20))

    def _file_row(self, parent, label, row, command):
        ctk.CTkLabel(parent, text=label).grid(row=row, column=0, padx=10, pady=5, sticky="w")
        entry = ctk.CTkEntry(parent, width=350)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ctk.CTkButton(parent, text="...", width=40, command=command).grid(row=row, column=2, padx=5)
        return entry

    def _browse_video(self):
        exts = " ".join(f"*{e}" for e in SUPPORTED_VIDEO_EXTENSIONS)
        path = filedialog.askopenfilename(filetypes=[("Video", exts)])
        if path:
            self.input_entry.delete(0, "end")
            self.input_entry.insert(0, path)

    def _browse_music(self):
        path = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.wav *.aac")])
        if path:
            self.music_path.delete(0, "end")
            self.music_path.insert(0, path)

    def _browse_logo(self):
        path = filedialog.askopenfilename(filetypes=[("Image", "*.png *.jpg *.jpeg *.webp")])
        if path:
            self.logo_path.delete(0, "end")
            self.logo_path.insert(0, path)

    def _browse_font(self):
        path = filedialog.askopenfilename(filetypes=[("Font", "*.ttf *.otf")])
        if path:
            self.font_path.delete(0, "end")
            self.font_path.insert(0, path)

    def _log(self, msg: str):
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")

    def _update_progress(self, step: str, pct: int):
        self.progress_bar.set(pct / 100)
        self.status_label.configure(text=step)
        self._log(f"[{pct}%] {step}")

    def _start_processing(self):
        video_path = self.input_entry.get().strip()
        if not video_path:
            self._log("Error: Select a video file first!")
            return
        if self._is_processing:
            return

        self._is_processing = True
        self.process_btn.configure(state="disabled", text="Processing...")
        self.log_text.delete("1.0", "end")
        self.progress_bar.set(0)

        thread = threading.Thread(target=self._process_thread, args=(video_path,), daemon=True)
        thread.start()

    def _process_thread(self, video_path: str):
        try:
            config = Config()
            config.max_clips = int(self.clips_slider.get())
            config.default_language = self.lang_var.get()
            config.whisper_model = self.model_var.get()

            music = self.music_path.get().strip() or None
            logo = self.logo_path.get().strip() or None
            font = self.font_path.get().strip() or None

            options = ProcessingOptions(
                format=self.format_var.get(),
                background_music=Path(music) if music else None,
                logo_path=Path(logo) if logo else None,
                font_path=Path(font) if font else None,
                animate_words=self.animate_var.get(),
            )

            result = run_pipeline(
                Path(video_path), config, options,
                progress_callback=lambda step, pct: self.after(0, self._update_progress, step, pct),
            )

            self.after(0, self._on_complete, result.clips)

        except Exception as e:
            self.after(0, self._on_error, str(e))

    def _on_complete(self, clips: list[Path]):
        self._is_processing = False
        self.process_btn.configure(state="normal", text="Create Clips")
        self.progress_bar.set(1.0)
        self.status_label.configure(text=f"Done! {len(clips)} clips created")
        self._log(f"\nDone! {len(clips)} clips saved:")
        for c in clips:
            self._log(f"  {c}")

    def _on_error(self, error: str):
        self._is_processing = False
        self.process_btn.configure(state="normal", text="Create Clips")
        self.status_label.configure(text="Error!")
        self._log(f"\nError: {error}")


def main():
    app = VideoCatApp()
    app.mainloop()


if __name__ == "__main__":
    main()
