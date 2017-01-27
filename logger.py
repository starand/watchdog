class Logger(object):
    def debug(self, message):
        print('[DBG] {0}'.format(message))

    def warning(self, message):
        print('[WARN] {0}'.format(message))

    def error(self, message):
        print('[ERR] {0}'.format(message))

    def info(self, message):
        print('[NFO] {0}'.format(message))

    def fatal(self, message):
        print('[FATAL] {0}'.format(message))

logger = Logger()
