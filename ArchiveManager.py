import os
import time
import shutil
import argparse
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime

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
        print("Start watching")
        event_handler = ChangeHandler(self)
        self.observer.schedule(event_handler, self.watch_path, recursive=True)
        self.observer.start()
        try:
            while True:
                time.sleep(self.monitor_interval)
        except KeyboardInterrupt:
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

class ChangeHandler(FileSystemEventHandler):
    def __init__(self, manager):
        self.manager = manager

    def on_modified(self, event):
        if event.is_directory:
            print(f"Directory modified: {event.src_path}")
        else:
            print(f"File modified: {event.src_path}")
            if event.src_path.endswith("global.json"):
                print(f"global.json modified: {event.src_path}")
                self.manager.global_json_modified = True
            elif event.src_path.endswith('.json') and event.src_path.startswith(os.path.join(self.manager.watch_path, 'round')):
                print(f"round file modified: {event.src_path}")
                print(f"Achive Saved")
                if self.manager.global_json_modified == True:
                    self.manager.archive_files()


    def on_created(self, event):
        if event.is_directory:
            print(f"New directory created: {event.src_path}")
        else:
            print(f"New file created: {event.src_path}")


def main():
    parser = argparse.ArgumentParser(description="File Archive Manager")
    subparsers = parser.add_subparsers(dest='command')

    # Watch subparser
    watch_parser = subparsers.add_parser('watch', help='Watch a directory for changes and archive files.')
    watch_parser.add_argument('--watch_path', type=str, default=r"C:\Users\18505\AppData\LocalLow\Double Cross\Sultan's Game\SAVE\76561199441913989", help='Path to the directory to watch.')
    watch_parser.add_argument('--archive_path', type=str, default=r"C:\Users\18505\AppData\LocalLow\Double Cross\Sultan's Game\SAVE\76561199441913989", help='Path to the archive directory.')
    watch_parser.add_argument('--save_path', type=str, default=r"D:\PythonProjects\utils\archives", help='Path to the save directory.')
    watch_parser.add_argument('--interval', type=float, default=1, help='Monitoring interval in seconds.')
    watch_parser.add_argument('--max-archives', type=int, default=30, help='Maximum number of archives to keep.')

    # Load subparser
    load_parser = subparsers.add_parser('load', help='Load an archive into the watched directory.')
    load_parser.add_argument('--watch_path', type=str, default=r"C:\Users\18505\AppData\LocalLow\Double Cross\Sultan's Game\SAVE\76561199441913989", help='Path to the directory to watch.')
    load_parser.add_argument('--archive_path', type=str, default=r"C:\Users\18505\AppData\LocalLow\Double Cross\Sultan's Game\SAVE\76561199441913989", help='Path to the archive directory.')
    load_parser.add_argument('--save_path', type=str, default=r"D:\PythonProjects\utils\archives", help='Path to the save directory.')
    load_parser.add_argument('--archive_name', type=str, help='Name of the archive to load.')

    args = parser.parse_args()

    if args.command == 'watch':
        manager = ArchiveManager(watch_path=args.watch_path, 
                                 archive_path=args.archive_path, 
                                 save_path=args.save_path, 
                                 monitor_interval=args.interval, 
                                 max_archives=args.max_archives)
        manager.start_watching()
    elif args.command == 'load':
        manager = ArchiveManager(watch_path=args.watch_path, 
                                 archive_path=args.archive_path, 
                                 save_path=args.save_path)
        manager.load_archive(args.archive_name)

if __name__ == "__main__":
    main()