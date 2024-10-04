import os
import sys
import time
import json
import shutil
import threading
from datetime import datetime


from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog


class ArchiveManager:
    def __init__(self, 
                 watch_path:str, 
                 archive_path:str, 
                 save_path:str, 
                 monitor_interval:float=1, 
                 max_archives:int=20):
        self.watch_path = watch_path
        self.archive_path = archive_path
        self.save_path = save_path
        self.monitor_interval = monitor_interval
        self.max_archives = max_archives
        self.observer = Observer()

        self.global_json_modified:bool = False
        
    def start_watching(self):
        self.observer_thread = threading.Thread(target=self._start_observing)
        self.observer_thread.start()

    def _start_observing(self):
        print("Start watching")
        event_handler = ChangeHandler(self)
        self.observer.schedule(event_handler, self.watch_path, recursive=True)
        self.observer.start()
        try:
            while True:
                time.sleep(self.monitor_interval)
        except Exception as e:
            print(e)
            self.observer.stop()
        self.observer.join()
    
    def stop_watching(self):
        print("Stop watching")
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
        
    def archive_files(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        save_folder = os.path.join(self.save_path, timestamp)
        os.makedirs(save_folder, exist_ok=True)
        
        for item in os.listdir(self.archive_path):
            s = os.path.join(self.archive_path, item)
            d = os.path.join(save_folder, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, False, None)
            else:
                shutil.copy2(s, d)

        self.global_json_modified = False
        self.cleanup_old_archives()

    def cleanup_old_archives(self):
        archives = sorted(os.listdir(self.save_path))
        while len(archives) > self.max_archives:
            shutil.rmtree(os.path.join(self.save_path, archives.pop(0)))

    def load_archive(self, archive_name):
        save_folder = os.path.join(self.save_path, archive_name)
        print(f"Loading archive from {save_folder}")
        if not os.path.exists(save_folder):
            print("Archive does not exist.")
            return

        for item in os.listdir(save_folder):
            s = os.path.join(save_folder, item)
            d = os.path.join(self.archive_path, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, True, None)
            else:
                shutil.copy2(s, d)

class ConfigManager:
    def __init__(self) -> None:
        self.config_file:str = "config.json"
        self.configs:dict = None
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                self.configs = json.load(f)
        else:
            self.initialize()
    
    def initialize(self):
        game_save_path = self.get_sultans_game_save_path()
        os.makedirs("archives", exist_ok=True)
        self.configs = {"watch_path": game_save_path, 
                        "archive_path": game_save_path, 
                        "save_path": "archives",
                        "monitor_interval": 1, 
                        "max_archives": 20, 
                        "auto_start": True}
        
    def __setattr__(self, name, value) -> None:
        super().__setattr__(name, value)
        if name == "configs" and value is not None:
            with open("config.json", "w") as f:
                json.dump(self.configs, f)

    def get_sultans_game_save_path(self):

        appdata_path = os.getenv('LOCALAPPDATA')
        if appdata_path.endswith("Local"):
            appdata_path = os.path.dirname(appdata_path)
        local_path = os.path.join(appdata_path, "Local")
        locallow_path = os.path.join(appdata_path, "LocalLow")

        if local_path:
            save_path_local = os.path.join(local_path, 'Double Cross', 'Sultan\'s Game', 'SAVE')
            if os.path.exists(save_path_local):
                return save_path_local

        if locallow_path:
            save_path_locallow = os.path.join(locallow_path, 'Double Cross', 'Sultan\'s Game', 'SAVE')
            if os.path.exists(save_path_locallow):
                return save_path_locallow
            
        return None

    

class ChangeHandler(FileSystemEventHandler):
    def __init__(self, manager):
        self.manager = manager

    def on_modified(self, event):
        if event.is_directory:
            print(f"Directory modified: {event.src_path}")
        else:
            print(f"File modified: {event.src_path}")
            if event.src_path.endswith('last_round_end.json'):
                print(f"global.json modified: {event.src_path}")
                print(os.path.join(self.manager.watch_path, 'round'))
                self.manager.global_json_modified = True
            elif "\\round_" in event.src_path:
                print(f"round file modified: {event.src_path}")
                print(f"Achive Saved")
                if self.manager.global_json_modified == True:
                    self.manager.archive_files()

    def on_created(self, event):
        if event.is_directory:
            print(f"New directory created: {event.src_path}")
        else:
            print(f"New file created: {event.src_path}")

class ArchiveApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sultan\'s Game Archive Manager")
        self.root.iconbitmap("icon.ico")

        self.archive_manager = None
        self.config_manager = ConfigManager()

        # Watch section
        self.watch_frame = tk.Frame(self.root)
        self.watch_frame.pack(pady=10)

        self.watch_path_label = tk.Label(self.watch_frame, text="Watch Path:")
        self.watch_path_label.grid(row=0, column=0)
        self.watch_path_entry = tk.Entry(self.watch_frame, width=50)
        self.watch_path_entry.grid(row=0, column=1)
        if self.config_manager.configs["watch_path"]:
            self.watch_path_entry.insert(0, self.config_manager.configs["watch_path"])
        self.watch_path_button = tk.Button(self.watch_frame, text="Browse", command=self.browse_watch_path)
        self.watch_path_button.grid(row=0, column=2)

        self.archive_path_label = tk.Label(self.watch_frame, text="Archive Path:")
        self.archive_path_label.grid(row=1, column=0)
        self.archive_path_entry = tk.Entry(self.watch_frame, width=50)
        self.archive_path_entry.grid(row=1, column=1)
        if self.config_manager.configs["archive_path"]:
            self.archive_path_entry.insert(0, self.config_manager.configs["archive_path"])
        self.archive_path_button = tk.Button(self.watch_frame, text="Browse", command=self.browse_archive_path)
        self.archive_path_button.grid(row=1, column=2)

        self.save_path_label = tk.Label(self.watch_frame, text="Save Path:")
        self.save_path_label.grid(row=2, column=0)
        self.save_path_entry = tk.Entry(self.watch_frame, width=50)
        self.save_path_entry.grid(row=2, column=1)
        if self.config_manager.configs["save_path"]:
            self.save_path_entry.insert(0, self.config_manager.configs["save_path"])
        self.save_path_button = tk.Button(self.watch_frame, text="Browse", command=self.browse_save_path)
        self.save_path_button.grid(row=2, column=2)

        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(pady=10)
        self.start_button = tk.Button(self.button_frame, text="Start Watching", command=self.start_watching)
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))
        self.stop_button = tk.Button(self.button_frame, text="Stop Watching", command=self.stop_watching)
        self.stop_button.pack(side=tk.LEFT)

        self.load_frame = tk.Frame(self.root)
        self.load_frame.pack(pady=10)

        self.load_archive_label = tk.Label(self.load_frame, text="Load Archive:")
        self.load_archive_label.grid(row=0, column=0)
        self.load_archive_entry = tk.Entry(self.load_frame, width=50)
        self.load_archive_entry.grid(row=0, column=1)
        self.load_browse_button = tk.Button(self.load_frame, text="Browse", command=self.browse_load_archive)
        self.load_browse_button.grid(row=0, column=2)
        self.load_button = tk.Button(self.load_frame, text="Load", command=self.load_archive)
        self.load_button.grid(row=0, column=3)

        
         # Collapsible frame for settings
        self.settings_frame = tk.LabelFrame(self.root, text="Settings")
        self.settings_frame.pack(pady=10, padx=10, fill="x")

        self.monitor_interval_label = tk.Label(self.settings_frame, text="Monitor Interval (s):")
        self.monitor_interval_label.grid(row=0, column=0)
        self.monitor_interval_entry = tk.Entry(self.settings_frame, width=10)
        self.monitor_interval_entry.grid(row=0, column=1)
        self.monitor_interval_entry.insert(0, str(self.config_manager.configs["monitor_interval"]))

        self.max_archives_label = tk.Label(self.settings_frame, text="Max Archives:")
        self.max_archives_label.grid(row=1, column=0)
        self.max_archives_entry = tk.Entry(self.settings_frame, width=10)
        self.max_archives_entry.grid(row=1, column=1)
        self.max_archives_entry.insert(0, str(self.config_manager.configs["max_archives"]))

        self.auto_start_var = tk.BooleanVar(value=self.config_manager.configs["auto_start"])
        self.auto_start_check = tk.Checkbutton(self.settings_frame, text="Auto start watching after load", variable=self.auto_start_var)
        self.auto_start_check.grid(row=2, column=0, columnspan=2)

        # Footer
        self.footer = tk.Label(self.root, text="Developed by Carzit", font=("Arial", 8))
        self.footer.pack(side=tk.BOTTOM, pady=10)
        
        

    def browse_watch_path(self):
        path = filedialog.askdirectory().replace("/", "\\")
        self.watch_path_entry.insert(0, path)
        self.config_manager.configs["watch_path"] = path

    def browse_archive_path(self):
        path = filedialog.askdirectory().replace("/", "\\")
        self.archive_path_entry.insert(0, path)
        self.config_manager.configs["archive_path"] = path

    def browse_save_path(self):
        path = filedialog.askdirectory().replace("/", "\\")
        self.save_path_entry.insert(0, path)
        self.config_manager.configs["save_path"] = path

    def browse_load_archive(self):
        save_path = self.save_path_entry.get()
        if not os.path.exists(save_path):
            messagebox.showerror("Error", "Invalid archive path.")
            return
        folder_name = filedialog.askdirectory(initialdir=save_path)
        if folder_name:
            self.load_archive_entry.delete(0, tk.END)
            self.load_archive_entry.insert(0, os.path.basename(folder_name))

    def start_watching(self):
        watch_path = self.watch_path_entry.get()
        archive_path = self.archive_path_entry.get()
        save_path = self.save_path_entry.get()
        if not os.path.exists(watch_path) or not os.path.exists(archive_path):
            messagebox.showerror("Error", "Invalid paths.")
            return
        self.archive_manager = ArchiveManager(watch_path=watch_path, 
                                              archive_path=archive_path, 
                                              save_path=save_path, 
                                              monitor_interval=float(self.monitor_interval_entry.get()), 
                                              max_archives=int(self.max_archives_entry.get()))
        self.config_manager.configs.update({"watch_path":watch_path, 
                                            "archive_path":archive_path, 
                                            "save_path":save_path, 
                                            "monitor_interval":float(self.monitor_interval_entry.get()), 
                                            "max_archives":int(self.max_archives_entry.get())})
        self.archive_manager.start_watching()
        self.start_button.config(state=tk.DISABLED)



    def stop_watching(self):
        if self.archive_manager:
            self.archive_manager.stop_watching()
            messagebox.showinfo("Stopped", "Stopped watching for changes.")
            self.start_button.config(state=tk.NORMAL)

    def load_archive(self):
        watch_path = self.watch_path_entry.get()
        archive_name = self.load_archive_entry.get()
        archive_path = self.archive_path_entry.get()
        save_path = self.save_path_entry.get()
        self.archive_manager = ArchiveManager(watch_path=watch_path, archive_path=archive_path, save_path=save_path)  # No watch path needed for loading
        self.archive_manager.load_archive(archive_name)

        if self.auto_start_var.get():
            self.start_watching()  # Automatically start watching if checked

if __name__ == "__main__":
    root = tk.Tk()
    root.protocol("WM_DELETE_WINDOW", lambda: sys.exit(-1))
    app = ArchiveApp(root)
    root.mainloop()