import json
import os
import threading
import requests
import customtkinter as ctk
from PIL import Image
import ollama_helper as helper

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

HISTORY = "temporary.json"

def load_history():
    if not os.path.exists(HISTORY):
        with open(HISTORY, "w") as f:
            json.dump({}, f)
    with open(HISTORY, "r") as f:
        return json.load(f)

def save_history(data):
    with open(HISTORY, "w") as f:
        json.dump(data, f, indent=2)

class OfflineChatBot(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Offline ChatBot - Version 1.0")
        self.geometry("800x600")
        self.resizable(False, False)

        # Images
        self.logo_photo = ctk.CTkImage(Image.open("logo.png").resize((50, 50)))
        self.edit_photo = ctk.CTkImage(Image.open("chat.png").resize((30, 30)))
        self.play_photo = ctk.CTkImage(Image.open("sent.png").resize((30, 30)))

        self.models = helper.get_list_models()
        self.current_model = self.models[0]
        self.chat_history = load_history()
        self.active_temp = True  # "Use past context" switch

        self._init_top_bar()
        self._init_model_selector()
        self._init_chat_display()
        self._init_input_area()

        # Session state
        self.current_chat_title = None     # Title of current chat (topic)
        self.running_thread = None

    def _init_top_bar(self):
        self.top_bar = ctk.CTkFrame(self, height=60, fg_color="#E5E6E8")
        self.top_bar.pack(fill="x", side="top")

        ctk.CTkLabel(self.top_bar, image=self.logo_photo, text="").place(x=10, y=5)
        self.title_label = ctk.CTkLabel(self.top_bar, text_color="black", font=("aptos", 18), text="New Chat")
        self.title_label.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkButton(self.top_bar, image=self.edit_photo, text="", width=10, fg_color="transparent",
                      hover=False, command=self.new_chat).place(x=750, y=15)

    def _init_model_selector(self):
        bar = ctk.CTkFrame(self, bg_color=self["bg"], fg_color=self["bg"])
        bar.pack(fill="x", side="top", padx=40, pady=(0, 5))

        ctk.CTkLabel(bar, text="MODEL: ", font=("aptos", 18), fg_color=self['bg']).pack(side="left", pady=4)
        self.select_model = ctk.StringVar(value=self.current_model)
        ctk.CTkOptionMenu(bar, variable=self.select_model, values=[m.upper() for m in self.models],
                          command=lambda val: self.change_model(val), width=200, font=("aptos", 18)).pack(side="left", padx=8)

        # TEMPORARY CHAT BUTTON ("use last messages as context")
        self.temp_btn = ctk.CTkButton(bar, text="Temporary Chat: OFF", fg_color="grey", command=self.toggle_temp)
        self.temp_btn.pack(side="right")

    def _init_chat_display(self):
        self.chat_display = ctk.CTkTextbox(self, height=420, width=750, font=("aptos", 16), wrap="word", fg_color="#1d1e1e")
        self.chat_display.pack(pady=(10, 0))
        self.chat_display.configure(state="disabled")
        self.chat_display.tag_config("user", foreground="white")
        self.chat_display.tag_config("bot", foreground="lightgreen")

    def _init_input_area(self):
        bottom = ctk.CTkFrame(self, height=50, fg_color="#707175")
        bottom.pack(fill="x", side="bottom", padx=10, pady=10)
        self.entry = ctk.CTkEntry(bottom, width=700, height=40, font=("aptos", 16))
        self.entry.pack(side="left", padx=(10, 0), pady=5)
        self.entry.bind("<Return>", self.send_message)
        self.send_btn = ctk.CTkButton(bottom, image=self.play_photo, text="️", fg_color="transparent",
                                      command=self.send_message)
        self.send_btn.pack(side="right", padx=10)

    def display_chat(self, message: str, tag="bot"):
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", message, tag)
        self.chat_display.see("end")
        self.chat_display.configure(state="disabled")

    def new_chat(self):
        self.title_label.configure(text="New Chat")
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.configure(state="disabled")
        self.current_chat_title = None
        self.entry.configure(state="normal")

    def change_model(self, value):
        self.current_model = value.lower()
        self.display_chat(f"\n[Model switched to {self.current_model}]\n")

    def toggle_temp(self):
        self.active_temp = not self.active_temp
        self.temp_btn.configure(text=f"Temporary Chat: {'OFF' if self.active_temp else 'ON'}",
            fg_color="gray" if self.active_temp else "green")

    def send_message(self, event=None):
        prompt = self.entry.get().strip()
        if not prompt:
            return

        # Set up new chat "title" if not set yet
        if not self.current_chat_title:
            title = helper.generate_title(prompt)
            self.current_chat_title = title
            self.title_label.configure(text=title)
            if title not in self.chat_history:
                self.chat_history[title] = []
                save_history(self.chat_history)

        self.display_chat(f"You: {prompt}\n", tag="user")
        self.entry.delete(0, "end")
        self.entry.configure(state="disabled")    # block input during answer

        def thread_fn():
            context = ""
            history_pairs = self.chat_history.get(self.current_chat_title, [])
            if self.active_temp and history_pairs:
                print(self.active_temp, "at history pairs")
                # Use prior pairs as explicit context
                context = "Based on our prior chat:\n"
                for msg in history_pairs:
                    context += f"USER: {msg['user say']}\nBOT: {msg['your answer']}\n"
                context += f"\nNow, USER: {prompt}\n"
            else:
                context = prompt
                explain = ""

            reply = helper.ask_ollama(context, model=self.current_model, stream=True)
            self.chat_display.after(0, lambda: self.display_chat(explain + f"{self.current_model.upper()}: {reply}\n\n"))

            # Store the pair
            to_store = {"user say": prompt, "your answer": reply}
            self.chat_history[self.current_chat_title].append(to_store)
            save_history(self.chat_history)
            self.entry.after(0, lambda: self.entry.configure(state="normal"))

        # Start chat/answer in a background thread
        threading.Thread(target=thread_fn, daemon=True).start()

if __name__ == "__main__":
    app = OfflineChatBot()
    app.mainloop()
