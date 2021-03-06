import os
import subprocess
from subprocess import Popen

from .helpers import get_auto_createrepo_status


def createrepo_unsafe(path, lock=None, dest_dir=None, base_url=None):
    """
        Run createrepo_c on the given path

        Warning! This function doesn't check user preferences.
        In most cases use `createrepo(...)`

    :param string path: target location to create repo
    :param lock: [optional]
    :param str dest_dir: [optional] relative to path location for repomd, in most cases
        you should also provide base_url.
    :param str base_url: optional parameter for createrepo_c, "--baseurl"

    :return tuple: (return_code,  stdout, stderr)
    """

    comm = ['/usr/bin/createrepo_c', '--database', '--ignore-lock']
    if os.path.exists(path + '/repodata/repomd.xml'):
        comm.append("--update")
    if "epel-5" in path:
        # this is because rhel-5 doesn't know sha256
        comm.extend(['-s', 'sha', '--checksum', 'md5'])

    if dest_dir:
        dest_dir_path = os.path.join(path, dest_dir)
        comm.extend(['--outputdir', dest_dir_path])
        if not os.path.exists(dest_dir_path):
            os.makedirs(dest_dir_path)

    if base_url:
        comm.extend(['--baseurl', base_url])

    comm.append(path)

    if lock:
        with lock:
            cmd = Popen(comm, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = cmd.communicate()
    else:
        cmd = Popen(comm, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = cmd.communicate()

    return cmd.returncode, out, err


def createrepo(path, front_url, username, projectname, base_url=None, lock=None):
    """
        Creates repo depending on the project setting "auto_createrepo".
        When enabled creates `repodata` at the provided path, otherwise

    :param path: directory with rpms
    :param front_url: url to the copr frontend
    :param username: copr project owner username
    :param projectname: copr project name
    :param base_url: base_url to access rpms independently of repomd location
    :param Multiprocessing.Lock lock:  [optional] global copr-backend lock

    :return: tuple(returncode, stdout, stderr) produced by `createrepo_c`
    """
    # TODO: add means of logging

    base_url = base_url or ""

    if get_auto_createrepo_status(front_url, username, projectname):
        return createrepo_unsafe(path, lock)
    else:
        return createrepo_unsafe(path, lock, base_url=base_url, dest_dir="devel")
