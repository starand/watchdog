from subprocess import Popen, PIPE
from os.path import dirname, abspath
from logger import logger


def callOutput(command):
    """
    Calls shell command and return output. Waits when command completed.
    """
    process = Popen(command, shell=True, stdout=PIPE)
    output, error = process.communicate()
    return output

def getScriptDir():
    """
    Returns path to main script folder
    """
    return dirname(abspath(__file__)) + '/'

def getFileContent(filename):
    try:
        return open(filename, 'r').read().strip()
    except IOError:
        logger.error('Unable to read from file {0}'.format(filename))
        return ""

def setFileContent(filename, data):
    try:
        fp = open(filename, 'w')
        fp.write('{0}'.format(data))
        fp.close()
        return True
    except IOError:
        logger.error('Unable to save data in file {0}'.format(filename))
        return False
