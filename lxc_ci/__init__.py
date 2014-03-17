from io import BytesIO
import glob
import json
import lxc
import os
import shutil
import subprocess
import sys
import tarfile
import time
import uuid

LXC_BUILD_DEPENDENCIES = set(["automake", "autoconf", "docbook2x", "doxygen",
                              "gcc", "graphviz", "libapparmor-dev",
                              "libcap-dev", "libcgmanager-dev",
                              "libgnutls-dev", "liblua5.2-dev",
                              "libseccomp-dev", "libselinux1-dev",
                              "linux-libc-dev", "lsb-release", "make",
                              "pkg-config", "python3-all-dev"])

LXC_RUN_DEPENDENCIES = set(["bridge-utils", "busybox-static", "cgmanager",
                            "cloud-image-utils", "curl", "dbus",
                            "debootstrap", "dnsmasq-base", "file",
                            "iptables", "openssl", "rpm", "rsync", "uidmap",
                            "uuid-runtime", "yum", "wget", "xz-utils"])


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

        self.container.set_config_item("lxc.aa_profile", "unconfined")

        # FIXME: Very ugly workaround
        import _lxc
        _lxc.Container.set_config_item(self.container, "lxc.mount.auto",
                                       "cgroup:mixed")

        print(" ==> Starting the container")
        if not self.container.start():
            raise Exception("Failed to start the container")

        if not self.container.get_ips(family="inet", timeout=90):
            raise Exception("Failed to connect to the container")

        self.container.set_cgroup_item("devices.allow", "b 7:* rwm")

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
            os.environ['HOME'] = '/root'

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
        sys.exit(0)

    def download(self, expr, target):
        rootfs = self.container.get_config_item("lxc.rootfs")
        match = glob.glob("%s/%s" % (rootfs, expr))

        for entry in match:
            print(" ==> Downloading: %s" % entry)
            path = target
            if os.path.isdir(target):
                path = "%s/%s" % (target, os.path.basename(entry))

            shutil.copy(entry, path)

            os.chown(path,
                     int(os.environ.get("SUDO_UID", os.geteuid())),
                     int(os.environ.get("SUDO_GID", os.getegid())))

    def upload(self, expr, target):
        rootfs = self.container.get_config_item("lxc.rootfs")
        match = glob.glob(expr)

        target = "%s/%s" % (rootfs, target)

        for entry in match:
            print(" ==> Uploading: %s" % entry)
            shutil.copy(entry, target)


def load_config(template, release, arch, variant):
    config = {}

    json_path = "templates/%s.json" % template
    if os.path.exists(json_path):
        with open(json_path, "r") as fd:
            config.update(json.loads(fd.read()))

    json_path = "templates/%s.%s.json" % (template, release)
    if os.path.exists(json_path):
        with open(json_path, "r") as fd:
            config.update(json.loads(fd.read()))

    template_args = config['template_args']
    config['template_args'] = []
    for arg in template_args:
        arg = arg.replace("RELEASE", release)
        arg = arg.replace("ARCH", config['template_arch'][arch])
        config['template_args'].append(arg)

    if isinstance(config['create_message'], list):
        config['create_message'] = "".join(config['create_message'])

    config['create_message'] = \
        config['create_message'].replace("RELEASE", release)

    config['create_message'] = \
        config['create_message'].replace("ARCH", arch)

    config['create_message'] = \
        config['create_message'].replace("VARIANT", variant)

    config['expiry'] = int(time.time()) + int(config['expiry']) * 86400

    return config


def generate_image_metadata(template, arch, config, target):
    tarball = tarfile.open("%s/meta.tar" % target, "w:")

    content = "%s\n" % config['expiry']
    expiry_file = tarfile.TarInfo()
    expiry_file.size = len(content)
    expiry_file.mtime = int(time.strftime("%s", time.localtime()))
    expiry_file.name = "expiry"
    tarball.addfile(expiry_file, BytesIO(content.encode('utf-8')))

    content = "%s\n" % config['create_message']
    create_message_file = tarfile.TarInfo()
    create_message_file.size = len(content)
    create_message_file.mtime = int(time.strftime("%s", time.localtime()))
    create_message_file.name = "create-message"
    tarball.addfile(create_message_file, BytesIO(content.encode('utf-8')))

    content = "%s\n" % "\n".join(sorted(config['templates']))
    templates_file = tarfile.TarInfo()
    templates_file.size = len(content)
    templates_file.mtime = int(time.strftime("%s", time.localtime()))
    templates_file.name = "templates"
    tarball.addfile(templates_file, BytesIO(content.encode('utf-8')))

    content = ""
    for conf in config['config_user']:
        content += "lxc.include = LXC_TEMPLATE_CONFIG/%s.%s.conf\n" \
            % (template, conf)
    if arch == "amd64":
        content += "lxc.arch = x86_64\n"
    elif arch == "i386":
        content += "lxc.arch = x86\n"
    config_user_file = tarfile.TarInfo()
    config_user_file.size = len(content)
    config_user_file.mtime = int(time.strftime("%s", time.localtime()))
    config_user_file.name = "config-user"
    tarball.addfile(config_user_file, BytesIO(content.encode('utf-8')))

    content = ""
    for conf in config['config_system']:
        content += "lxc.include = LXC_TEMPLATE_CONFIG/%s.%s.conf\n" \
            % (template, conf)
    if arch == "amd64":
        content += "lxc.arch = x86_64\n"
    elif arch == "i386":
        content += "lxc.arch = x86\n"
    config_system_file = tarfile.TarInfo()
    config_system_file.size = len(content)
    config_system_file.mtime = int(time.strftime("%s", time.localtime()))
    config_system_file.name = "config"
    tarball.addfile(config_system_file, BytesIO(content.encode('utf-8')))

    content = "%s\n" % "\n".join(sorted(config['exclude_user']))
    exclude_user_file = tarfile.TarInfo()
    exclude_user_file.size = len(content)
    exclude_user_file.mtime = int(time.strftime("%s", time.localtime()))
    exclude_user_file.name = "excludes-user"
    tarball.addfile(exclude_user_file, BytesIO(content.encode('utf-8')))

    tarball.close()
    if os.path.exists("%s/meta.tar.xz" % target):
        os.remove("%s/meta.tar.xz" % target)
    subprocess.call(["xz", "-9", "%s/meta.tar" % target])

    os.chown("%s/meta.tar.xz" % target,
             int(os.environ.get("SUDO_UID", os.geteuid())),
             int(os.environ.get("SUDO_GID", os.getegid())))
