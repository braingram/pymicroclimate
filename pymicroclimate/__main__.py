import sys

from . import logger


if __name__ == '__main__':
    if len(sys.argv) > 1:
        cmd = sys.argv.pop(1)
    else:
        cmd = 'log'
    if cmd == 'log':
        logger.run_cmdline()
    elif cmd == 'ui':
        raise NotImplementedError("No UI yet")
    else:
        raise ValueError("Unknown command %s" % (cmd, ))
