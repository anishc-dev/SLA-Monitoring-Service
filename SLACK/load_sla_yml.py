import yaml
import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from logger import info, error, set_operation, set_correlation_id, start_timer
import uuid


class SLAConfigManager:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config = {}
        self.observer = Observer()
        self.event_handler = FileSystemEventHandler()
        start_timer()
        set_operation("sla_config_manager_initialization")
        self.load_config()
        info("SLAConfigManager initialized")

    def load_config(self):
        start_timer()
        set_operation("sla_config_loading")
        set_correlation_id(str(uuid.uuid4()))
        try:
            with open(self.config_path, 'r') as file:
                self.config = yaml.safe_load(file)
            info("SLA configuration loaded successfully", config_path=self.config_path)
        except FileNotFoundError:
            error("SLA configuration file not found", config_path=self.config_path)
            self.config = {}
        except yaml.YAMLError as e:
            error("Error parsing SLA configuration file", error=str(e))
            self.config = {}
        except Exception as e:
            error("Unexpected error loading SLA configuration", error=str(e))
            self.config = {}

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

    def get_config(self):
        start_timer()
        set_operation("config_retrieval")
        info("Configuration retrieved", config_keys=list(self.config.keys()) if self.config else [])
        return self.config

config_manager = SLAConfigManager("SLACK/sla_config.yml")
config_manager.start()

if __name__ == "__main__":
    set_operation("sla_config_manager_standalone")
    config_manager = SLAConfigManager("SLACK/sla_config.yml")
    config_manager.start()
    while True:
        time.sleep(1)
