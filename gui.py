import json
import os.path
import time
import requests
import customtkinter as ctk
from PIL import Image
import threading
import ollama_helper as helper


# Configure CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

HISTORY = "temporary.json"

def json_loading():
    if not os.path.exists(HISTORY):
        with open(HISTORY, "w") as f:
            json.dump({}, f)
        return json.load({})

    with open(HISTORY, "r") as f:
        return json.load(f)

# Create TITLE using content "CONTENT". only one line

class OfflineChatBot(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.active_temp = self.stop_flag = self.clean_flag = False
        self.title("Offline ChatBot - Version 1.0")
        self.geometry("800x600")
        self.resizable(False, False)

        # supports
        font_18 = "aptos", 18
        self.common = {"height": 40, "font": ("aptos", 16)}
        self.is_title = False
        self.store_data = {}

        # LOGO IMAGE
        logo_img = Image.open("logo.png").resize((80, 80))
        self.logo_photo = ctk.CTkImage(logo_img, size=(50, 50))
        # NEW CHAT IMAGE
        edit_img = Image.open("chat.png").resize((30, 30))
        self.edit_photo = ctk.CTkImage(edit_img)
        # SENT IMAGE
        play_img = Image.open("sent.png").resize((50, 50))
        self.play_photo = ctk.CTkImage(play_img, size=(30, 30))

        # Top Bar
        self.top_bar = ctk.CTkFrame(self, height=60, fg_color="#E5E6E8")
        self.top_bar.pack(fill="x", side="top")

        # Left logo
        self.logo_label = ctk.CTkLabel(self.top_bar, image=self.logo_photo, text="")
        self.logo_label.place(x=10, y=5)

        # Project title
        self.title_label = ctk.CTkLabel(self.top_bar, text_color="black", font=font_18, text="New Chat")
        self.title_label.place(relx=0.5, rely=0.5, anchor="center")

        # Edit icon (right side)
        self.edit_btn = ctk.CTkButton(self.top_bar, image=self.edit_photo, text="", width=10, fg_color="transparent",
                                      hover=False, command=self.new_chat, font=font_18)
        self.edit_btn.place(x=750, y=15)

        # MIDDLE - MODEL AREA
        self.ribbon_frame = ctk.CTkFrame(self, bg_color=self["bg"], fg_color=self["bg"])
        self.ribbon_frame.pack(fill="x", side="top", padx=40)

        ctk.CTkLabel(self.ribbon_frame, text="MODEL: ", font=font_18, fg_color=self['bg']).pack(side="left", pady=4)
        self.select_model = ctk.StringVar()

        threading.Thread(target=helper, daemon=True).start()
        self.list_models: list = helper.get_list_models()
        # self.list_models: list = ["llama3.2:latest", "deepseek-r1:671b"]
        max_len = max(len(x) for x in self.list_models)

        self.models_name = ctk.CTkOptionMenu(self.ribbon_frame, anchor="center", variable=self.select_model, height=30,
                                             values=[name.upper() for name in self.list_models], width=max_len * 10,
                                             command=self.start_model, font=font_18, fg_color=self["bg"])
        self.models_name.pack(side="left", anchor="center", pady=4)
        self.models_name.set(self.list_models[0].upper())

        self.temporary_btn = ctk.CTkButton(self.ribbon_frame, text="Temporary Chat", hover=self["bg"], fg_color="grey",
                                           command=lambda: self.change_bool("temp"))
        self.temporary_btn.pack(side="right", anchor="e", pady=4)

        # Chat display area
        self.chat_display = ctk.CTkTextbox(self, height=420, width=750, font=font_18, wrap="word", fg_color="#1d1e1e")
        self.chat_display.pack(pady=(10, 0))
        self.chat_display.configure(state="disabled")
        self.chat_display.tag_config("user", foreground="white")
        self.chat_display.tag_config("bot", foreground="lightgreen")

        # Bottom area - Entry + Send
        self.bottom_frame = ctk.CTkFrame(self, height=50, fg_color="#707175")
        self.bottom_frame.pack(fill="x", side="bottom", padx=10, pady=10)

        self.entry = ctk.CTkEntry(self.bottom_frame, width=700, **self.common)
        self.entry.pack(side="left", padx=(10, 0), pady=5)
        self.entry.bind("<Return>", self.send_message)

        self.send_btn = ctk.CTkButton(self.bottom_frame, image=self.play_photo, text="️", command=self.send_message,
                                      fg_color="transparent")
        self.send_btn.pack(side="right", padx=10)

    @staticmethod
    def store_records(mode="w", *, data):
        match mode:
            case "w":
                with open("temporary.json", mode) as f:
                    json.dump(data, f, indent=4)
                    return None
            case "r":
                with open("temporary.json", mode) as f:
                    return json.load(f)
        raise ValueError(f"{mode} is not a valid mode. use of 'w' or 'r'.")

    def new_chat(self):
        self.models_name.set(self.list_models[0].upper())
        self.clean_flag = True
        self.stop_flag = True
        self.title_label.configure(text="New Chat")
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.configure(state="disabled")
        self.is_title = False
        self.store_records("w", data=self.store_data)
        self.store_data.clear()
        self.models_name.configure(state="normal")

    def send_message(self, event=None): # type: ignore
        prompt = self.entry.get().strip()
        if prompt == "":
            return
        self.title_generator(prompt) if not self.is_title else None
        self.display_chat(f"You: {prompt}\n\n")
        self.entry.delete(0, "end")
        self.entry.configure(state="disabled")
        self.chat_display.update()
        self.ask_ollama(prompt)
        self.send_btn.configure(command=self.send_message)
        self.entry.configure(state="normal")

    def display_chat(self, message: str):
        self.chat_display.configure(state="normal")

        if message.startswith("You:"):
            self.chat_display.insert("end", f"{message}", "user")
        else:
            self.chat_display.insert("end", f"{message}", "bot")
        self.chat_display.see("end")
        self.chat_display.configure(state="disabled")

    def start_model(self, event=None):
        self.display_chat(f"Starting {self.select_model.get().split(':')[0]}! please hold...\n")
        self.chat_display.update()
        try:
            # tag = helper.starter(self.select_model.get().lower())
            tag = 'helper.starter(self.select_model.get().lower())'
        except Exception as e:
            print(e)
        else:
            self.display_chat(f"{tag}\n")

    def change_bool(self, mode):
        match mode:
            case "stop":
                self.stop_flag = True
            case "clean":
                self.clean_flag = True
            case "temp":
                self.active_temp = False if self.active_temp else True
                if self.active_temp:
                    self.temporary_btn.configure(fg_color="green")
                else:
                    self.temporary_btn.configure(fg_color="grey")

    def ask_ollama(self, prompt):
        if self.active_temp:
            prompt, taken = self.use_temp(prompt)
        else:
            taken = prompt
        self.models_name.configure(state="disabled")
        try:
            res = requests.post("http://localhost:11434/api/generate", stream=True,
                                json={"model": self.select_model.get(), "prompt": taken, "stream": True})

            full_reply = ""
            self.display_chat(f"{self.select_model.get().split(':')[0]}: ".upper())

            self.send_btn.configure(command=lambda: self.change_bool("stop"))
            for line in res.iter_lines():
                if self.clean_flag:
                    print("->>")
                    break
                if self.stop_flag:
                    self.display_chat("\n[PROCESS STOPPED]")
                    break
                if line:
                    part = json.loads(line.decode('utf-8')).get("response", "")
                    full_reply += part
                    self.display_chat(part)
                    self.update()

            self.display_chat("\n\n")
            self.stop_flag = False
            self.clean_flag = False
            if self.active_temp:
                self.store_data[self.fetch_last()].append({"user say": prompt, "your answer": full_reply})
            self.models_name.configure(state="normal")
            return full_reply

        except Exception as e:
            return f"[Error: {e}]"

    def title_generator(self, content: str):
        title = "title" # helper.generate_title(content)
        self.is_title = True
        self.store_data[title] = []
        self.title_label.configure(text=title)
        self.title_label.update()

    def fetch_last(self):
        return list(self.store_data.keys())[-1]

    def use_temp(self, prompt):
        if self.store_data[self.fetch_last()]:
            new_prompt = f"Based on last chats {self.store_data[self.fetch_last()]}\n\nuser say -> {prompt}"
            return prompt, new_prompt
        else:
            return prompt, prompt


if __name__ == "__main__":
    app = OfflineChatBot()
    app.mainloop()
    print(app.store_data)
