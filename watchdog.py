import sys
from os.path import join
from os import path
from signal import signal, pause, SIGINT, SIGTERM, SIG_IGN, SIGHUP

from daemon import Daemon
from process_guard import ProcessGuard
from config import cfg
import wdutils
from logger import logger


class WatchdogDaemon(Daemon):
    pgList = []
    running = False

    def __init__(self):
        self.currentDir = wdutils.getScriptDir()
        pidFileName = join(self.currentDir, cfg.getOption('watchdog', 'pidfile'))

        scriptName = __file__
        Daemon.__init__(self, pidFileName, scriptName)
        # Don't initialize logger here because it registers an atexit() handler
        # which interferes with the daemonization/forking process.
        # Namely, the atexit handler is called in both the parent and forked process
        # leading to hangs in resource deletion code.

    def run(self):
        """
        Sets signal handlers and start working treads. Waits for signal to stop.
        """
        #logger.initialize(self.config_file, '{0}_watchdog'.format(cfg.getOption('subprocess', 'name')), consoleSeverity=logger.SEVERITY_NONE)
        #logger.important.info("=== Start. Ver: " + version.ProductVersion + " Application path: " + join(self.currentDir+ path.basename(__file__)))

        # TODO: validate sp name & binary there
        #if not self.subprocessBinary:
            #logger.error("Subprocess binary was not set in watchdog.ini file")
            #sys.exit(-1)

        self.running = True
        # Start subprocesses
        spList = cfg.getSubprocesses()
        for sp in spList:
            processGuard = ProcessGuard(self, sp)
            processGuard.start()
            self.pgList.append(processGuard)

        self.setSignalHandlers()

        pause()

        self.running = False
        for pg in self.pgList:
            pg.stop()
        #logger.important.info("=== Exit")

    def signalHandler(self, signum, frame):
        pass

    def setSignalHandlers(self):
        """
        Sets signal handlers for SIGTERM and SIGINT signals.
        Sets handlers to ignore SIGHUP.
        """
        signal(SIGTERM, self.signalHandler)
        signal(SIGINT, self.signalHandler)
        # ignore next signals to prevent stopping of daemon
        for sig in (SIGHUP, ):
            signal(sig, SIG_IGN)


def start(watchdog):
    """
    Start watchdog daemon. Show error message if start failed or if it was started before.
    """
    pid = watchdog.getPid()
    if pid:
        print('Already started. Pid : {0}'.format(pid))
    else:
        watchdog.start()
        pid = watchdog.getPid()
        if not pid:
            print('Could not start daemon')

def stop(watchdog):
    """
    Stop watchdog daemon. Show error message if daemon is not running or if it is not possible to stop daemon.
    """
    pid = watchdog.getPid()
    if not pid:
        print('Daemon is not running')
    else:
        watchdog.stop()
        pid = watchdog.getPid()
        if pid:
            print('Could not stop watchdog. Pid : {0}'.format(pid))

def restart(watchdog):
    """
    Restart watchdog daemon. Show message in case daemon is not running or if it is not possible to start daemon.
    """
    pid = watchdog.getPid()
    if not pid:
        print('Watchdog is not running. Starting ..')
        start(watchdog)
    else:
        watchdog.restart()
    pid = watchdog.getPid()
    if not pid:
        print('Unable to start watchdog')

def status(watchdog):
    """
    Show status of watchdog daemon.
    """
    pid = watchdog.getPid()
    if pid:
        print('Watchdog is running. Pid: {0}'.format(pid))
    else:
        print('Watchdog is not running')

def help():
    helpString = """python watchdog.py [options]

    start   - start watchdog daemon
    stop    - stop watchdog daemon
    restart - restart watchdog daemon
    status  - retrieve watchdog status

    help    - show help
    """
    print(helpString)


if __name__ == '__main__':
    start_commands = 'start', 'run'
    stop_commands = 'stop', 'exit', 'close'
    restart_commands = 'restart', 're'
    status_commands = 'status', 'stat'
    help_commands = 'help', '-h', '--help'

    from sys import argv
    command = 'status'
    if len(argv) > 1:
        command = argv[-1]

    watchdog = WatchdogDaemon()

    if command in status_commands:
        status(watchdog)
    elif command in stop_commands:
        stop(watchdog)
    elif command in start_commands:
        start(watchdog)
    elif command in restart_commands:
        restart(watchdog)
    elif command in help_commands:
        help()
    else:
        print("Unknown command '{0}'".format(command))
