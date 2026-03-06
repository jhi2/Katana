import os
import shutil as sh
import subprocess as sub
import json

class ConfigManager:
    def __init__(self):
        pass

    def check_config(self,dir):
        if os.path.exists(dir):
            return True
        else:
            return False
    def save_config(self,dir):
        if self.check_config(dir):
            sh.copy(dir, dir + ".bak")
        with open(dir, "w") as f:
            json.dump(self.config, f, indent=4)
    def load_config(self,dir):
        if self.check_config(dir):
            with open(dir, "r") as f:
                self.config = json.load(f)
        else:
            self.save_config(dir)