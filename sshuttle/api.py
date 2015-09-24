import copy
import os
import subprocess
import time
import tempfile

import sshuttle

PKGDIR = os.path.dirname(sshuttle.__file__)
POST_START_SLEEP = 3


class ShuttleSetup(object):
    def __init__(self, username, server, subnet, verbose, identity):
        self.username = username
        self.server = server
        self.subnet = subnet
        self.verbose = verbose
        self.identity = identity

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        for attr in ['username', 'server', 'subnet', 'verbose', 'identity']:
            if getattr(self, attr) != getattr(other, attr):
                return False
        return True


class Shuttle(object):
    def __init__(self):
        self.process = None
        self.id_filepath = None
        self.setup = None

    def start_shuttling(self, username, server,
                        subnet='0/0',
                        verbose=True,
                        identity=None):
        setup = ShuttleSetup(username, server, subnet, verbose, identity)

        if setup == self.setup:
            return

        self.setup = setup

        if self.id_filepath:
            os.remove(self.id_filepath)

        if self.process:
            self.process.kill()

        self.env = copy.deepcopy(os.environ)

        if setup.identity:
            self._create_agent()
        # TODO shuttle process watchdog
        self.process = self._create_shuttle_process()
        # HACK should somehow figure out when the routing is done
        time.sleep(POST_START_SLEEP)

    def _create_shuttle_process(self):
        """
        return a subprocess.Popen for a process running an sshuttle client
        """
        binary = os.path.join(PKGDIR, "sshuttle")
        target = "{}@{}".format(self.setup.username, self.setup.server)
        args = [binary, "-r", target, self.setup.subnet]

        if self.setup.verbose:
            args.append("-vv")

        # HACK ssh into the node once to trust its key
        subprocess.Popen(["ssh", "-i", self.id_filepath,
                          "-oStrictHostKeyChecking=no", target, "echo"]).wait()
        return subprocess.Popen(args,
                                cwd=PKGDIR,
                                env=self.env,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

    def _create_agent(self):
        """
        setup an SSH agent with the Shuttle's identity
        """
        for line in subprocess.check_output(["ssh-agent"]).split("\n"):
            for cmd in line.split(";"):
                if "export" in cmd:
                    continue
                parts = cmd.split("=")
                key, value = parts[0], "=".join(parts[1:])

                if key and value:
                    self.env[key] = value

        with tempfile.NamedTemporaryFile(delete=False) as f:
            self.id_filepath = f.name
            f.write(self.setup.identity)

        return subprocess.Popen(["ssh-add", self.id_filepath],
                                env=self.env).wait()
