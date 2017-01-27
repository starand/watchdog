import os
import ConfigParser
import wdutils
import json
import sys


_defaults = {
    'watchdog' : {
        'pidfile' : 'pid'
    },

    'subprocess' : {
        'statefile' : 'state',
        'exit_error_message_file' : 'error_file',
        'max_stop_timeout' : 10,
        'stderr_file' : 'stderr_file'
    },

    'pg' : {
        'check_interval_sec' : 1
    }
}


class Config(object):
    config = None
    subprocesses = []

    def __init__(self):
        configFile = os.path.join(wdutils.getScriptDir(), 'wd.cfg')
        try:
            with open(configFile) as json_file:
                self.config = json.load(json_file)
            self.parseSubprocesses()
        except ValueError as ex:
            sys.exit("Invalid json {0}".format(ex))

    def getJsonOption(self, section, key):
        value = None
        try:
            value = self.config[section][key]
        except KeyError:
            None
        return value

    def getDefaultOption(self, section, key):
        result = None
        if section in _defaults:
            values = _defaults[section]
            if key in values:
                result = values[key]
        return result

    def getOption(self, section, key):
        value = self.getJsonOption(section, key)
        if not value:
            value = self.getDefaultOption(section, key)
        return value

    def parseSubprocesses(self):
        for sp in self.config["subprocesses"]:
            subprocess = { "name" : sp["name"], "binary" : sp["binary"] }
            self.subprocesses.append(subprocess)

    def getSubprocesses(self):
        return self.subprocesses


cfg = Config()
