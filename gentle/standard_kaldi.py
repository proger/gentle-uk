import subprocess
import os
import logging

from .util.paths import get_binary

EXECUTABLE_PATH = get_binary("ext/k3")
logger = logging.getLogger(__name__)

class Kaldi:
    def __init__(self, exp, hclg_path):
        cmd = [EXECUTABLE_PATH]
        
        cmd.append(str(exp / 'chain'))
        cmd.append(str(exp / 'langdir'))
        cmd.append(str(hclg_path))

        if not os.path.exists(hclg_path):
            logger.error('hclg_path does not exist: %s', hclg_path)
        self._p = subprocess.Popen(cmd,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)
        self.finished = False

    def _cmd(self, c):
        self._p.stdin.write(("%s\n" % (c)).encode())
        self._p.stdin.flush()

    def push_chunk(self, buf):
        # Wait until we're ready
        self._cmd("push-chunk")
        
        cnt = int(len(buf)/2)
        self._cmd(str(cnt))
        self._p.stdin.write(buf) #arr.tostring())
        status = self._p.stdout.readline().strip().decode()
        return status == 'ok'

    def get_final(self):
        self._cmd("get-final")
        words = []
        while True:
            line = self._p.stdout.readline().decode()
            if line.startswith("done"):
                break
            parts = line.split(' / ')
            if line.startswith('word'):
                wd = {}
                wd['word'] = parts[0].split(': ')[1]
                wd['start'] = float(parts[1].split(': ')[1])
                wd['duration'] = float(parts[2].split(': ')[1])
                wd['phones'] = []
                words.append(wd)
            elif line.startswith('phone'):
                ph = {}
                ph['phone'] = parts[0].split(': ')[1]
                ph['duration'] = float(parts[1].split(': ')[1])
                words[-1]['phones'].append(ph)

        self._reset()

        print('words', [word['word'] for word in words])
        return words

    def _reset(self):
        self._cmd("reset")

    def stop(self):
        if not self.finished:
            self.finished = True
            self._cmd("stop")
            self._p.stdin.close()
            self._p.stdout.close()
            self._p.wait()

    def __del__(self):
        self.stop()
