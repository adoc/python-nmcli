#!/usr/bin/env python
# -*- encoding: utf-8 -*-

"""
module: nmcli
short_description: Wrapper around nmcli executable itself
description:
        Execute nmcli command to gather information about network manager
        devices.


--------------------------------------------------------------------------------

Original Work
https://github.com/migonzalvar/ansible-nmcli/blob/master/library/nmcli
Copyright (C) 2013 Miguel González (https://github.com/migonzalvar/)

Derivative Works:
https://github.com/ZachGoldberg/python-nmcli
Copyright (c) Zach Goldberg (https://github.com/ZachGoldberg)

https://github.com/adoc/python-nmcli
Copyright (c) C. Nicholas Long (https://github.com/adoc)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


import shlex
import subprocess


__all__ = ["nm", "dev", "con"]


DOCUMENTATION = """
    ---
    module: nmcli
    short_description: Wrapper around nmcli executable itself
    description:
        - Execute nmcli command to gather information about network manager
          devices.
    """


NMCLI_FIELDS = {
    'nm': "RUNNING STATE WIFI-HARDWARE WIFI WWAN-HARDWARE WWAN".split(),
    'dev': "DEVICE TYPE STATE".split(),
    'con': "NAME UUID TYPE TIMESTAMP-REAL".split(),
    'con status': "NAME UUID DEVICES DEFAULT VPN MASTER-PATH".split(),
    'con list id': (
        "connection,802-3-ethernet,802-1x,802-11-wireless," +
        "802-11-wireless-security,ipv4,ipv6,serial,ppp,pppoe," +
        "gsm,cdma,bluetooth,802-11-olpc-mesh,vpn,infiniband,bond," +
        "vlan").split(",")
}


NMCLI_MULTILINE_KEYS = ('con list id',)


def _shell(args):
    """Execute args and returns status code, stdout and stderr

    Any exceptions in running subprocess are allowed to raise to caller
    """
    process = subprocess.Popen(args, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    retcode = process.returncode

    return retcode, stdout, stderr


def _nmcli(obj, command=None, fields=None, multiline=False):
    """Wraps nmcli execution"""

    ns = [obj, command]
    ns.extend(fields or [])

    def _build_fields(ns, fields, multiline):
        try:
            fields = NMCLI_FIELDS[' '.join(ns)]
            if fields in NMCLI_MULTILINE_KEYS:
                multiline = True
        except KeyError:
            ns.pop()
            ns, fields, multiline = _build_fields(ns, fields, multiline)
        return ns, fields, multiline

    _, fields, multiline = _build_fields(ns, fields, multiline)

    args = ['nmcli', '--terse', '--fields', ",".join(fields), obj or ""]

    if command:
        args += shlex.split(command)

    retcode, stdout, stderr = _shell(args)

    data = []
    if retcode == 0:
        if multiline:
            # prev_field = None
            row = {}
            for line in stdout.split('\n'):
                values = line.split(':', 1)
                if len(values) == 2:
                    multikey, value = values
                    field, prop = multikey.split('.')
                    row[prop] = value
            data.append(row)
        else:
            for line in stdout.split('\n'):
                values = line.split(':')
                if len(values) == len(fields):
                    row = dict(zip(fields, values))
                    data.append(row)
        return data
    else:
        msg = "nmcli return {0} code. STDERR='{1}'".format(retcode, stderr)
        raise Exception(msg)


class _NMCommand(object):
    def __init__(self, cmdname, commands):
        self.cmdname = cmdname
        for command, possibleargs in commands:
            setattr(self, command, self.gen_action(command, possibleargs))

    def gen_action(self, command, possibleargs):
        def sanitize_args(args):
            def sanitize_arg(arg):
                if isinstance(arg, bool):
                    return str(arg).lower()

                if isinstance(arg, int):
                    return str(arg)

                if arg is not None:
                    return arg.lower()

                return arg

            if isinstance(args, list):
                newargs = []
                for arg in args:
                    newargs.append(sanitize_arg(arg))
                return newargs
            else:
                return sanitize_arg(args)

        usableargs = sanitize_args(possibleargs)

        def verify_arg(arg):
            arg = sanitize_args(arg)
            if arg not in usableargs:
                raise Exception(
                    "%s is not a valid argument for '%s'. Parameters: %s" % (
                        arg, command, possibleargs))
            return arg

        def verify_args(args):
            return [verify_arg(arg) for arg in args]

        def run_action(args=None, **kwargs):
            if args is None:
                args = []

            if not isinstance(args, list):
                args = [args]

            if kwargs:
                args.extend(kwargs.keys())

            args = verify_args(args)

            if not args:
                cmd = command
            else:
                opts = []
                for arg in args:
                    if arg not in kwargs:
                        opts.append(arg)
                    else:
                        opts.append("%s %s" % (
                                arg,
                                sanitize_args(kwargs[arg])))
                cmd = "%s %s" % (command,
                                 ' '.join(opts))

            return _nmcli(self.cmdname,
                         command=cmd)

        return run_action


#todo: I'm sure there is a way to introspect all of this from nmcli itself.
nm = _NMCommand(
        "nm",
        [("status", None),
         ("enable", [True, False]),
         ("sleep", [True, False]),
         ("wifi", ["on", "off"]),
         ("wwan", ["on", "off"])]
        )


con = _NMCommand(
    "con",
    [("list", [None, "id", "uuid"]),
     ("status", [None, "id", "uuid", "path"]),
     ("up", ["id", "uuid", "iface", "ap"]),
     ("down", ["id", "uuid"]),
     ("delete", ["id", "uuid"]),
    ])


dev = _NMCommand(
    "dev",
    [("status", None),
     ("list", [None, "iface"]),
     ("disconnect", ["iface"]),
     ("wifi", ["list"]),
    ])


if __name__ == '__main__':
    # Tests.
    print (nm.status())
    print (nm.enable(True))
    print (nm.enable(False))

    try:
        print (con.list(food=8302))
        print ("BAD!")
    except:
        pass

    try:
        print nm.enable("asdasd")
        print ("BAD!")
    except:
        pass

    print (nm.enable(True))