import yaml
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from logger import info, set_operation, set_correlation_id
import uuid


class SLAConfigManager:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config = {}
        self.observer = Observer()
        self.event_handler = FileSystemEventHandler()

    def load_config(self):
        set_operation("sla_config_loading")
        set_correlation_id(str(uuid.uuid4()))
        with open(self.config_path, 'r') as file:
            self.config = yaml.safe_load(file)
        info("Config loaded successfully", config_path=self.config_path)

    def on_modified(self, event):
        if event.src_path == self.config_path:
            set_operation("sla_config_file_modified")
            set_correlation_id(str(uuid.uuid4()))
            info("Config file modified, reloading", config_path=self.config_path)
            self.load_config()

    def start(self):
        set_operation("sla_config_watcher_start")
        set_correlation_id(str(uuid.uuid4()))
        self.load_config()
        self.observer.schedule(self.event_handler, path=self.config_path, recursive=False)
        self.observer.start()
        info("Config file watcher started", config_path=self.config_path)

config_manager = SLAConfigManager("SLACK/sla_config.yml")
config_manager.start()

if __name__ == "__main__":
    set_operation("sla_config_manager_standalone")
    config_manager = SLAConfigManager("SLACK/sla_config.yml")
    config_manager.start()
    while True:
        time.sleep(1)
