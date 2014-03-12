import glob
import lxc
import os
import shutil
import subprocess
import sys
import uuid

LXC_DEPENDENCIES = set(["automake", "autoconf", "docbook2x", "doxygen",
                        "gcc", "graphviz", "libapparmor-dev",
                        "libcap-dev", "libcgmanager-dev",
                        "libgnutls-dev", "liblua5.2-dev",
                        "libseccomp-dev", "libselinux1-dev",
                        "linux-libc-dev", "lsb-release", "make", "pkg-config",
                        "python3-all-dev"])


class BuildEnvironment:
    architecture = None
    container = None
    distribution = None
    release = None

    def __init__(self, distribution, release, architecture=None):
        if not architecture:
            dpkg = subprocess.Popen(['dpkg', '--print-architecture'],
                                    stdout=subprocess.PIPE,
                                    universal_newlines=True)
            if dpkg.wait() != 0:
                raise Exception("dpkg failure")

            architecture = dpkg.stdout.read().strip()

        self.distribution = distribution
        self.release = release
        self.architecture = architecture

        self.container = lxc.Container(str(uuid.uuid1()))
        print(" ==> Defined %s as %s %s %s" %
              (self.container.name,
               self.distribution,
               self.release,
               self.architecture))

    def setup(self):
        print(" ==> Creating rootfs")
        if not self.container.create("download", lxc.LXC_CREATE_QUIET,
                                     {'dist': self.distribution,
                                      'release': self.release,
                                      'arch': self.architecture}):
            raise Exception("Failed to create the rootfs")

        print(" ==> Starting the container")
        if not self.container.start():
            raise Exception("Failed to start the container")

        if not self.container.get_ips(family="inet", timeout=30):
            raise Exception("Failed to connect to the container")

        self.execute(["mkdir", "-p", "/build"])
        self.update()

    def update(self):
        print(" ==> Updating the container")
        if self.distribution == "ubuntu":
            if self.execute(["apt-get", "update"]) != 0 or \
               self.execute(["apt-get", "dist-upgrade",
                             "-y", "--force-yes"]) != 0:
                raise Exception("Failed to update the container")

    def cleanup(self):
        print(" ==> Cleaning up the environment")
        if not self.container or not self.container.defined:
            return

        if self.container.running:
            self.container.stop()

        self.container.destroy()

    def execute(self, cmd, cwd="/"):
        def run_command(args):
            cmd, cwd = args

            os.environ['PATH'] = '/usr/sbin:/usr/bin:/sbin:/bin'

            return subprocess.call(cmd, cwd=cwd)

        if isinstance(cmd, str):
            rootfs = self.container.get_config_item("lxc.rootfs")
            cmdpath = "%s/tmp/exec_script" % rootfs
            with open(cmdpath, "w+") as fd:
                fd.write(cmd)
            os.chmod(cmdpath, 0o755)
            cmd = ["/tmp/exec_script"]

        print(" ==> Executing: \"%s\" in %s" % (" ".join(cmd), cwd))
        return self.container.attach_wait(run_command,
                                          (cmd, cwd),
                                          env_policy=lxc.LXC_ATTACH_CLEAR_ENV)

    def install(self, pkgs):
        print(" ==> Installing: %s" % (", ".join(pkgs)))
        if self.distribution != "ubuntu":
            raise Exception("Unsupported distribution for package installs")

        return self.execute(["apt-get", "install", "-y", "--force-yes"] + pkgs)

    def exit_pass(self):
        self.cleanup()
        print(" ==> Exitting with status PASS")
        sys.exit(0)

    def exit_fail(self):
        self.cleanup()
        print(" ==> Exitting with status FAIL")
        sys.exit(1)

    def exit_unstable(self):
        self.cleanup()
        print(" ==> Exitting with status UNSTABLE")
        sys.exit(2)

    def download(self, expr, target):
        rootfs = self.container.get_config_item("lxc.rootfs")
        match = glob.glob("%s/%s" % (rootfs, expr))

        for entry in match:
            print(" ==> Downloading: %s" % entry)
            shutil.copy(entry, target)

    def upload(self, expr, target):
        rootfs = self.container.get_config_item("lxc.rootfs")
        match = glob.glob(expr)

        target = "%s/%s" % (rootfs, target)

        for entry in match:
            print(" ==> Uploading: %s" % entry)
            shutil.copy(entry, target)
