import os
from threading import Thread
from time import sleep
from subprocess import Popen, PIPE
from signal import SIGKILL, SIGINT

import wdutils
from config import cfg

from logger import logger


STATUS_STOPPED = 1
STATUS_RUNNING = 2


class ProcessGuard(object):
    def __init__(self, watchdog, config):
        execFile = config["binary"]
        self.execFile = execFile if os.path.isabs(execFile) else os.path.join(wdutils.getScriptDir(), execFile)
        self.stateFile = watchdog.currentDir + cfg.getOption('subprocess', 'statefile')
        self.subprocessName = cfg.getOption('subprocess', 'name')
        self.checkInterval = cfg.getOption('pg', 'check_interval_sec')
        self.maxStopTimeout = cfg.getOption('subprocess', 'max_stop_timeout')
        self.exitErrorMessageFile = cfg.getOption('subprocess', 'exit_error_message_file')
        if self.exitErrorMessageFile and not os.path.isabs(self.exitErrorMessageFile):
            self.exitErrorMessageFile = os.path.join(wdutils.getScriptDir(), self.exitErrorMessageFile)
        self.stderrFile = os.path.join(os.path.dirname(self.exitErrorMessageFile), cfg.getOption('subprocess', 'stderr_file'))

        self.watchdog = watchdog
        self.config = config
        self.subprocess = None
        self.setInitialState()
	os.environ['LD_LIBRARY_PATH'] = os.path.dirname(self.execFile)

    def setInitialState(self):
        """
        Sets initial subprocess state. Tries to get it from file.
        """
        stateFromFile = self.getStateFromFile()
        self.setState(stateFromFile if stateFromFile else STATUS_STOPPED)

    def getStateFromFile(self):
        """
        Reads subprocess state from file if it is possible otherwise return None.
        """
        state = wdutils.getFileContent(self.stateFile)
        return int(state) if state else None

    def setStateToFile(self, state):
        """
        Writes subprocess state to file.
        """
        return wdutils.setFileContent(self.stateFile, state)

    def getProcessID(self):
        return self.subprocess.pid if self.subprocess else None

    def processIsRunning(self):
        return self.subprocess is not None and self.subprocess.poll() is None

    def processFailed(self):
        return self.subprocess is not None and self.subprocess.poll() is not None

    def getFailedMessage(self):
        """
        Check exit error message file, stdout file and exit code and compose failed message.
        """
        errorMessage = ''
        try:
            with open(self.exitErrorMessageFile) as errorFile:
                errorMessage = errorFile.read()
        except IOError:
            pass
        try:
            with open(self.stderrFile) as stderrFile:
                errorMessage += stderrFile.read()
        except IOError:
            pass
        if len(errorMessage):
                errorMessage += ' '
        # add exit code inforamtion
        if self.subprocess.returncode == -6:
            errorMessage += "SIGABRT received"
        elif self.subprocess.returncode == -9:
            errorMessage += "SIGKILL received"
        elif self.subprocess.returncode == -11:
            errorMessage += "Segmentation fault"
        else:
            errorMessage += "exit code {0}".format(self.subprocess.returncode)
        return errorMessage if errorMessage else 'Unexpected termination of {0}'.format(self.subprocessName)

    def openStderrFile(self):
        """
        Open file for subprocess.Popen stderr param.
        """
        self.error_file = PIPE
        try:
            if self.stderrFile:
                self.error_file =  open(self.stderrFile, 'w')
        except IOError:
            pass
        return self.error_file

    def setState(self, state):
        self.state = state
        self.setStateToFile(state)

    def getExpectedState(self):
        return self.state

    def getActualState(self):
        """
        Returns current state of subprocess.
        """
        return STATUS_RUNNING if self.processIsRunning() else STATUS_STOPPED

    def startProcess(self):
        """
        Starts subprocess process if it is not running.
        """
        result = True
        if not self.processIsRunning():
            try:
                index = '--{0}-index'.format(self.config["name"])
                command = [self.execFile, '--exit-error-message-file', self.exitErrorMessageFile]
                if self.execFile[-3:] == '.py':
                    command.insert(0, 'python')
                logger.info('Starting {0}'.format(' '.join(command)))
                self.subprocess = Popen(command, close_fds=True, stderr=self.openStderrFile())
                self.setState(STATUS_RUNNING)
            except OSError as error:
                logger.error('{0} (Error code: {1})'.format(error.strerror, error.errno))
                self.subprocess = None
                result =  False
        return result

    def stopProcess(self, hardStop = False):
        """
        Stops subprocess process if it is running by SIGINT signal sending.
        """
        pid = self.getProcessID()
        if pid:
            logger.info('Stopping subprocess ({0}), hardbit : {1}'.format(pid, hardStop))
            try:
                os.kill(int(pid), SIGKILL if hardStop else SIGINT)
                self.setState(STATUS_STOPPED)
            except OSError:
                pass
            self.subprocess = None
        return True

    def stopProcessWhenWatchdogStopped(self):
        """
        Stops subprocess process if it is running by SIGINT signal sending.
        """
        pid = self.getProcessID()
        if pid:
            logger.info('Stopping subprocess ({0})'.format(pid))
            try:
                self.subprocess.terminate()
                #self.setState(STATUS_STOPPED)
                wait_seconds = 0
                while self.processIsRunning():
                    if wait_seconds == self.maxStopTimeout:
                        self.subprocess.kill()
                        logger.error('Subprocess ({0}; {1}) was killed'.format(self.subprocessName, pid))
                    wait_seconds += 1
                    sleep(1)
            except Exception:
                pass
            self.subprocess = None
        return True

    def restartProcess(self, hardStop = False):
        return self.stopProcess(hardStop) and self.startProcess()

    def checkSubprocessFailed(self):
        if self.processFailed():
            message = self.getFailedMessage()
            logger.error('Process {0} failed : {1}'.format(self.config["name"], message))

    def trackProcess(self):
        """
        Checks subprocess process state in a loop.
        """
        while self.watchdog.running:
            if self.getExpectedState() == STATUS_RUNNING and not self.processIsRunning():
                self.checkSubprocessFailed()
                self.startProcess()
            elif self.getExpectedState() == STATUS_STOPPED and self.processIsRunning():
                self.stopProcess()
            sleep(self.checkInterval)

    def start(self):
        thread = Thread(target=self.trackProcess)
        thread.start()

    def stop(self):
        self.stopProcessWhenWatchdogStopped()
