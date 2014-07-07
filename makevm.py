#!/usr/bin/env python

import argparse
import subprocess
import sys
import time

import os.path
from xml.etree import ElementTree as ET

import libvirt


GREEN_TEXT = "\033[32m{}\033[0m"


def msg_line(text):
    print >> sys.stderr, GREEN_TEXT.format(text),


def msg(text):
    print >> sys.stderr, GREEN_TEXT.format(text)


def main(base_vm, name, passthrough_dir=None):
    conn = libvirt.open()
    domain = conn.lookupByName(base_vm)
    xml_root = ET.fromstring(domain.XMLDesc())
    disk_img_path = xml_root.find("devices/disk/source").get("file")
    disk_img_dir = os.path.dirname(disk_img_path)
    new_disk_path = os.path.join(disk_img_dir, name + ".qcow2")
    if os.path.exists(new_disk_path):
        print >> sys.stderr, \
            "error: disk image \"{}\" already exists.".format(new_disk_path)
        sys.exit(1)

    msg("Creating disk image {} (overlaying {}):".format(
        new_disk_path,
        disk_img_path,
    ))
    subprocess.check_call([
        "/usr/bin/qemu-img",
        "create",
        "-f", "qcow2",
        "-b", disk_img_path,
        new_disk_path,
    ])

    xml_root.find("name").text = name

    # clear uuid (will be autoregenerated)
    xml_root.find("uuid").text = ""

    # clear network interface mac address (will be autoregenerated)
    interface = xml_root.find("devices/interface").remove(
        xml_root.find("devices/interface/mac")
    )
    xml_root.find("devices/disk/source").set("file", new_disk_path)

    if passthrough_dir is not None:
        passthrough_dir = os.path.abspath(passthrough_dir)
        passthrough = ET.fromstring(
            """
            <filesystem type='mount' accessmode='squash'>
              <source dir=''/>
              <target dir='shared'/>
              <readonly/>
            </filesystem>
            """
        )
        passthrough.find("source").set("dir", passthrough_dir)
        xml_root.find("devices").append(passthrough)
        msg("Configured read-only access to {}.".format(passthrough_dir))

    msg_line("Creating VM...")
    conn.defineXML(ET.tostring(xml_root))
    msg("done.")

    msg_line("Booting VM...")
    new_domain = conn.lookupByName(name)
    new_domain.create()
    msg("done.")

    # hack to avoid occasional race where the console can't be opened yet.
    # (the OS is probably still booting anyway)
    time.sleep(3)
    msg("Running ./sysprep.sh:")
    subprocess.check_call([
        "./sysprep.sh",
        name,
        "true" if passthrough_dir is not None else "false"
    ])

    print
    msg("VM \"{}\" setup complete.".format(name))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Quickly create a new cloned VM.",
    )
    parser.add_argument(
        "base_vm",
        metavar="BASE_VM",
        type=str,
        help="a base VM to clone",
    )
    parser.add_argument(
        "name",
        metavar="NAME",
        type=str,
        help="name of new VM",
    )
    parser.add_argument(
        "-d", "--passthrough_dir",
        metavar="SHARED_DIR",
        type=str,
        default=None,
        help="read-only shared passthrough directory",
    )
    args = parser.parse_args()
    main(**vars(args))
