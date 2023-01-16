#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import warnings
import re
import shutil
import stat
import ctypes
import psutil

warnings.filterwarnings("ignore", category=DeprecationWarning)

try:
    #pylint: disable=import-error
    import apt
except ModuleNotFoundError:
    pass

#Make linux_distribution available from some suitable package, falling back to returning that we don't know.
try:
    from distro import linux_distribution
except:
    try:
        #pylint: disable=no-name-in-module
        from platform import linux_distribution
    except:
        def linux_distribution():
            return ("unknown",)

def log(*args, **kwargs):
    """logging function that flushes"""
    print(*args, **kwargs)
    sys.stdout.flush()


class SetupError(Exception):
    pass


class WindowsUninstaller():
    def __init__(self):
        self.uninstaller = None
        self.uninstaller_path = None

    def __can_uninstall(self):
        ip = os.path.join(os.environ["ProgramFiles"], "Safir SDK Core")
        uninstaller = os.path.join(ip, "Uninstall.exe")
        installed = os.path.isfile(uninstaller) and len(os.listdir(ip)) > 1

        pf86 = os.environ.get("ProgramFiles(x86)")

        if pf86 is None:
            if installed:
                self.uninstaller = uninstaller
                self.uninstaller_path = ip
        else:
            ip86 = os.path.join(pf86, "Safir SDK Core")
            uninstaller86 = os.path.join(ip86, "Uninstall.exe")
            installed86 = os.path.isfile(uninstaller86) and len(os.listdir(ip86)) > 1

            if installed86 and installed:
                raise SetupError("Multiple installs found!")
            elif installed:
                self.uninstaller = uninstaller
                self.uninstaller_path = ip
            elif installed86:
                self.uninstaller = uninstaller86
                self.uninstaller_path = ip86

        return self.uninstaller is not None

    def uninstall(self):
        if not self.__can_uninstall():
            log("No installation found, don't need to uninstall anything")
            return

        log("It looks like Safir SDK Core is installed! Will uninstall!")

        log("Running uninstaller:", self.uninstaller)
        #The _? argument requires that we concatenate the command like this instead of using a tuple
        result = subprocess.call((self.uninstaller + " /S _?=" + self.uninstaller_path))
        if result != 0:
            raise SetupError("Uninstaller failed (" + str(result) + ")!")

        if os.path.isdir(os.path.join(self.uninstaller_path, "dou")):
            raise SetupError("Installer dir " + self.uninstaller_path + " still exists after uninstallation! Contents:\n" +
                             str(os.listdir(self.uninstaller_path)))
        uninstallerdir = os.path.dirname(self.uninstaller)
        if os.path.isdir(os.path.join(uninstallerdir, "dou")):
            raise SetupError("Uninstaller dir " + uninstallerdir + " still exists after uninstallation! Contents:\n" +
                             str(os.listdir(uninstallerdir)))

class DebianUninstaller():
    def __init__(self):
        self.packages = ("safir-sdk-core", "safir-sdk-core-tools", "safir-sdk-core-dev", "safir-sdk-core-testsuite")

    def __is_installed(self, package_name, cache=None):
        if cache is None:
            cache = apt.cache.Cache()

        return cache.has_key(package_name) and \
          cache[package_name].is_installed

    def __can_uninstall(self):
        cache = apt.cache.Cache()
        for pkg in self.packages:
            if self.__is_installed(pkg, cache):
                return True
        return False

    def uninstall(self):
        if not self.__can_uninstall():
            log("No installation found, don't need to uninstall anything")
            return

        log("It looks like Safir SDK Core is installed! Will uninstall!")

        log("Uninstalling packages: ")

        cmd = ["sudo", "--non-interactive", "apt-get", "--yes", "purge"]
        for pkg in self.packages:
            if self.__is_installed(pkg):
                log(" ", pkg)
                cmd.append(pkg)

        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as proc:
            output = proc.communicate()[0]
            if proc.returncode != 0:
                raise SetupError("Failed to run apt-get purge. returncode = " + str(proc.returncode) + "\nOutput:\n" +
                                 output.decode("utf-8"))

def kill_safir_processes():
    #a list of tuples (regex, regex), the pattern first will be matched with the process
    #name, and the second pattern with all the command line arguments (concatenated
    #together with a space between each)
    patterns = [("dose_main",""),
                ("dope_main",""),
                ("safir_control",""),
                ("foreach",""),
                ("dose_test_sequencer",""),
                ("dose_test_cpp",""),
                ("java","-jar dose_test_java"),
                ("mono","dose_test_dotnet"), #on linux the process is named mono
                ("dose_test_dotnet","")] #and on windows it is named dose_test_dotnet
    #for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    #    log (f"process {proc.info['name']}: '{type(proc.info['cmdline'])}', '{proc.info['cmdline']}'")
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        cmdline = "" if proc.info["cmdline"] is None else " ".join(proc.info["cmdline"])
        if len(cmdline) > 0:
            for name_pat, args_pat in patterns:
                if re.search(name_pat, proc.info['name']) and re.search(args_pat, cmdline):
                    log(f"Killing process {proc.info['name']}: '{cmdline}'")
                    proc.kill()


def delete_workspace():
    def onerror(function, path, excinfo):
        try:
            # path contains the path of the file that couldn't be removed
            # let's just assume that it's read-only and unlink it.
            if os.path.isfile(path):
                os.chmod(path, stat.S_IWUSR|stat.S_IRUSR)
            os.unlink( path )
            return
        except Exception as e:
            log(f"Caught exception in onerror: {e}")

        #hmm, maybe the path is very long and we're on windows
        try:
            if sys.platform == "win32":
                newpath = "\\\\?\\" + os.path.join(os.getcwd(),path)
                os.chmod(newpath, stat.S_IWRITE)
                os.unlink(newpath)
                return
        except Exception as e:
            log(f"Caught exception in win32 part of onerror: {e}")

        #ok, if we're on windows we can try to mark it for removal and reboot
        if sys.platform == "win32":
            log("Marking file for deletion on reboot:",path)
            MOVEFILE_DELAY_UNTIL_REBOOT = 4
            newpath = "\\\\?\\" + os.path.join(os.getcwd(),path)
            ctypes.windll.kernel32.MoveFileExA(newpath, None,
                                               MOVEFILE_DELAY_UNTIL_REBOOT)
            return
        raise SetupError(f"Failed to delete {path}")

    workspace_dir = os.getcwd()
    log(f"Workspace dir is {workspace_dir}")
    if "workspace" not in workspace_dir:
        raise SetupError("No 'workspace' in the path")
    while "workspace" in workspace_dir:
        workspace_dir = os.path.abspath(os.path.join(workspace_dir, os.pardir))
    workspace_dir = os.path.join(workspace_dir, "workspace")
    log(f"Will delete workspace directories in {workspace_dir}")
    os.chdir(workspace_dir)
    for ws_subdir in os.listdir("."):
        if os.path.abspath(ws_subdir) in os.environ["WORKSPACE"] or \
           os.path.abspath(ws_subdir) in os.environ["WORKSPACE_TMP"]:
            log(f"Skipping directory '{ws_subdir}' in {workspace_dir}")
            continue
        if not os.path.isdir(ws_subdir):
            log(f"Skipping file '{ws_subdir}' in {workspace_dir}")
            continue
        log(f"Deleting directory '{ws_subdir}' in {workspace_dir}")
        shutil.rmtree(ws_subdir,onerror=onerror)

def main():
    try:
        log("--- Killing any leftover Safir processes ---")
        kill_safir_processes()

        log("--- Uninstalling any leftover Safir installations ---")
        if sys.platform == "win32":
            uninstaller = WindowsUninstaller()
        elif sys.platform.startswith("linux") and \
             linux_distribution()[0] in  ("Debian GNU/Linux", "Ubuntu"):
            uninstaller = DebianUninstaller()
        else:
            log("Platform", sys.platform, ",", linux_distribution(), " is not supported by this script")
            return 1

        uninstaller.uninstall()

        log("--- Deleting workspaces ---")
        delete_workspace()

    except SetupError as e:
        log("Error: " + str(e))
        return 1
    except Exception as e:
        log("Caught exception: " + str(e))
        return 1
    return 0


sys.exit(main())
