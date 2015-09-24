import copy
import os
import subprocess

import sshuttle

PKGDIR = os.path.dirname(sshuttle.__file__)


class Shuttle(object):
    def __init__(self, username, server,
                 subnet='0/0',
                 verbose=True,
                 keyfile=None):
        self.username = username
        self.server = server
        self.subnet = subnet
        self.env = copy.deepcopy(os.environ)
        self.verbose = verbose

        self.keyfile = keyfile

        if keyfile:
            self._create_agent()
        # TODO shuttle process watchdog
        self.process = self._create_shuttle_process()

    def _create_shuttle_process(self):
        """
        return a subprocess.Popen for a process running an sshuttle client
        """
        binary = os.path.join(PKGDIR, "sshuttle")
        args = [binary, "-r", "{}@{}".format(self.username, self.server),
                self.subnet]

        if self.verbose:
            args.append("-vv")

        return subprocess.Popen(args,
                                cwd=PKGDIR,
                                env=self.env,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

    def _create_agent(self):
        """
        setup an SSH agent with the Shuttle's keyfile
        """
        for line in subprocess.check_output(["ssh-agent"]).split("\n"):
            for cmd in line.split(";"):
                if "export" in cmd:
                    continue
                parts = cmd.split("=")
                key, value = parts[0], "=".join(parts[1:])

                if key and value:
                    print ((key, value))
                    self.env[key] = value

        return subprocess.Popen(["ssh-add", self.keyfile], env=self.env).wait()
