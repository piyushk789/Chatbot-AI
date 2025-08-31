import json
import os
import shutil
import threading
import subprocess
import customtkinter as ctk
from PIL import Image
import ollama_helper as helper
from tkinter import messagebox

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

HISTORY_FILE = "temporary.json"

def load_history():
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "w") as f:
            json.dump({}, f)
    with open(HISTORY_FILE, "r") as f:
        return json.load(f)

def save_history(data):
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=2)

class OfflineChatBot(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Offline ChatBot - Version 1.0")
        self.geometry("1000x600")  # Increased width for sidebar
        self.resizable(False, False)

        # Images
        self.logo_photo = ctk.CTkImage(Image.open("logo.png").resize((50, 50)))
        self.edit_photo = ctk.CTkImage(Image.open("chat.png").resize((30, 30)))
        self.play_photo = ctk.CTkImage(Image.open("sent.png").resize((30, 30)))

        # Data and State
        try:
            self.models = helper.get_list_models()
        except ValueError as e:
            messagebox.showinfo("Module Error", "No models found. Please add a model using 'ollama pull <model_name>' command.")
        except ConnectionError as e:
            messagebox.showerror("Ollama Error", "Ollama is not installed or not working. Please check your Ollama installation.")

        self.current_model = self.models[0] if self.models else "N/A"
        self.chat_history = load_history()
        self.active_temp = True  # Use conversation context by default
        self.current_chat_title = None
        self.is_generating = False

        # --- Main Layout ---
        self._init_sidebar()
        self._init_chat_area()

        # Populate sidebar with existing chats
        self._populate_sidebar()

    def _init_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=200, fg_color="#2a2d2e")
        self.sidebar_frame.pack(side="left", fill="y", padx=(5, 0), pady=5)

        # Sidebar Header
        sidebar_header = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        sidebar_header.pack(pady=10, padx=10, fill="x")

        ctk.CTkLabel(sidebar_header, text="Chats", font=("aptos", 18, "bold")).pack(side="left")

        # New Chat button in sidebar
        ctk.CTkButton(sidebar_header, image=self.edit_photo, text="", width=30, fg_color="transparent",
                      hover_color="#444", command=self.new_chat).pack(side="right")

        # Scrollable area for chat titles
        self.sidebar_scroll_area = ctk.CTkScrollableFrame(self.sidebar_frame, fg_color="transparent")
        self.sidebar_scroll_area.pack(expand=True, fill="both", padx=5, pady=5)

    def _init_chat_area(self):
        # This frame will contain everything to the right of the sidebar
        chat_main_frame = ctk.CTkFrame(self, fg_color=self["bg"])
        chat_main_frame.pack(side="right", fill="both", expand=True)

        self._init_top_bar(chat_main_frame)
        self._init_model_selector(chat_main_frame)
        self._init_chat_display(chat_main_frame)
        self._init_input_area(chat_main_frame)

    # Note: These `_init` methods now take a `parent` frame
    def _init_top_bar(self, parent):
        self.top_bar = ctk.CTkFrame(parent, height=60, fg_color="#E5E6E8", corner_radius=0)
        self.top_bar.pack(fill="x", side="top")
        self.title_label = ctk.CTkLabel(self.top_bar, text_color="black", font=("aptos", 18), text="New Chat")
        self.title_label.place(relx=0.5, rely=0.5, anchor="center")

    def _init_model_selector(self, parent):
        bar = ctk.CTkFrame(parent, fg_color=self["bg"])
        bar.pack(fill="x", side="top", padx=20, pady=(10, 5))
        ctk.CTkLabel(bar, text="MODEL: ", font=("aptos", 16)).pack(side="left")
        self.select_model = ctk.StringVar(value=self.current_model.upper())
        ctk.CTkOptionMenu(bar, variable=self.select_model, values=[m.upper() for m in self.models],
                          command=self.change_model, width=200).pack(side="left", padx=8)
        self.temp_btn = ctk.CTkButton(bar, text="Context: ON", fg_color="green", command=self.toggle_temp)
        self.temp_btn.pack(side="right")

    def _init_chat_display(self, parent):
        self.chat_display = ctk.CTkTextbox(parent, font=("aptos", 16), wrap="word", fg_color="#1d1e1e")
        self.chat_display.pack(expand=True, fill="both", padx=20, pady=(5, 10))
        self.chat_display.configure(state="disabled")
        self.chat_display.tag_config("user", foreground="white")
        self.chat_display.tag_config("bot", foreground="lightgreen")
        self.chat_display.tag_config("system", foreground="orange")

    def _init_input_area(self, parent):
        bottom = ctk.CTkFrame(parent, height=50, fg_color="#333333")
        bottom.pack(fill="x", side="bottom", padx=20, pady=(0, 20))
        self.entry = ctk.CTkEntry(bottom, height=40, font=("aptos", 16), placeholder_text="Ask me anything...")
        self.entry.pack(expand=True, fill="x", side="left", padx=(10, 0), pady=10)
        self.entry.bind("<Return>", self.send_message)
        self.send_btn = ctk.CTkButton(bottom, image=self.play_photo, text="", fg_color="transparent",
                                      hover_color="#444", width=40, command=self.send_message)
        self.send_btn.pack(side="right", padx=10, pady=10)

    def _populate_sidebar(self):
        # Clear existing buttons
        for widget in self.sidebar_scroll_area.winfo_children():
            widget.destroy()

        # Add a button for each chat title
        chat_titles = list(self.chat_history.keys())
        for title in reversed(chat_titles):  # Show newest first
            btn = ctk.CTkButton(self.sidebar_scroll_area, text=title, anchor="w", fg_color="transparent",
                command=lambda t=title: self._load_chat(t))
            btn.pack(fill="x", pady=2)

    def _load_chat(self, title):
        if self.is_generating: return

        self.current_chat_title = title
        self.title_label.configure(text=title)

        # Clear and load history into display
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")

        chat_session = self.chat_history.get(title, [])
        for entry in chat_session:
            self.display_chat(f"You: {entry['user say']}\n", tag="user", clear=False)
            self.display_chat(f"Bot: {entry['your answer']}\n\n", tag="bot", clear=False)

        self.chat_display.configure(state="disabled")
        self.entry.configure(state="normal")
        self.entry.focus()

    def display_chat(self, message: str, tag="bot", clear=False):
        self.chat_display.configure(state="normal")
        if clear: self.chat_display.delete("1.0", "end")
        self.chat_display.insert("end", message, tag)
        self.chat_display.see("end")
        self.chat_display.configure(state="disabled")

    def new_chat(self):
        if self.is_generating: return
        self.title_label.configure(text="New Chat")
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.configure(state="disabled")
        self.current_chat_title = None
        self.entry.configure(state="normal")
        self.entry.focus()

    def change_model(self, value):
        self.current_model = value.lower()
        self.display_chat(f"\n[Model switched to {self.current_model}]\n\n", tag="system")

    def toggle_temp(self):
        self.active_temp = not self.active_temp
        self.temp_btn.configure(
            text=f"Context: {'ON' if self.active_temp else 'OFF'}",
            fg_color="green" if self.active_temp else "gray"
        )

    def send_message(self, event=None):
        prompt = self.entry.get().strip()
        if not prompt or self.is_generating:
            return

        self.entry.delete(0, "end")
        self.display_chat(f"You: {prompt}\n", tag="user")

        self.entry.configure(state="disabled")
        self.is_generating = True

        def generation_thread():
            try:
                # If this is a new chat, generate and set a title
                if not self.current_chat_title:
                    title = helper.generate_title(prompt)
                    self.current_chat_title = title
                    self.chat_history[title] = []
                    # Update UI in main thread
                    self.after(0, lambda: self.title_label.configure(text=title))
                    self.after(0, self._populate_sidebar)

                # Prepare context if needed
                context = prompt
                history_pairs = self.chat_history.get(self.current_chat_title, [])
                if self.active_temp and history_pairs:
                    context_str = "Based on our prior chat:\n"
                    for msg in history_pairs[-3:]:  # Use last 3 exchanges for context
                        context_str += f"USER: {msg['user say']}\nBOT: {msg['your answer']}\n"
                    context = f"{context_str}\nNow, USER asks: {prompt}"
                    self.after(0, lambda: self.display_chat("[Using conversation context...]\n", tag="system"))

                # Get response from Ollama
                self.after(0, lambda: self.display_chat(f"{self.current_model.upper()}: ", tag="bot"))
                reply = helper.ask_ollama(context, model=self.current_model, stream=True)
                self.after(0, lambda: self.display_chat(reply + "\n\n", tag="bot"))

                # Save history
                self.chat_history[self.current_chat_title].append({"user say": prompt, "your answer": reply})
                save_history(self.chat_history)

            except Exception as e:
                self.after(0, lambda: self.display_chat(f"\n[Error: {e}]\n", tag="system"))
            finally:
                # Re-enable input in main thread
                self.after(0, lambda: self.entry.configure(state="normal"))
                self.is_generating = False

        threading.Thread(target=generation_thread, daemon=True).start()


if __name__ == "__main__":
    path = shutil.which("ollama")
    if path:
        subprocess.Popen(f"{path} serve")
        app = OfflineChatBot()
        app.mainloop()
    else:
        print(f"'Ollama' is not recognized as an internal or external command, operable program or batch file.")

