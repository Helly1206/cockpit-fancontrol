#!/usr/bin/python3

# -*- coding: utf-8 -*-
#########################################################
# SERVICE : fancontrol-cli.py                           #
#           Commandline interface for automating        #
#           fancontrol for commandline or app.          #
#           I. Helwegen 2023                            #
#########################################################

####################### IMPORTS #########################
import sys
import os
import json
import subprocess
from datahandler import datahandler

#########################################################

####################### GLOBALS #########################
VERSION      = "0.80"
DAEMONSFC    = "fancontrol"
CMDNOTEXIST  = 127
CMDTIMEOUT   = 124
SYSTEMCTL    = "systemctl"
CTLSTART     = SYSTEMCTL + " start"
CTLSTOP      = SYSTEMCTL + " stop"
CTLRELOAD    = SYSTEMCTL + " reload"
CTLRESTART   = SYSTEMCTL + " restart"
CTLENABLE    = SYSTEMCTL + " enable"
CTLDISABLE   = SYSTEMCTL + " disable"
CTLSTATUS    = SYSTEMCTL + " status"
CTLISACTIVE  = SYSTEMCTL + " is-active"
CTLISENABLED = SYSTEMCTL + " is-enabled"
#########################################################

###################### FUNCTIONS ########################

#########################################################
# Class : shell                                         #
#########################################################
class shell(object):
    def __init__(self):
        pass

    def __del__(self):
        pass

    def runCommand(self, cmd, input = None, timeout = None):
        CMDNOTEXIST = 127, "", ""
        if input:
            input = input.encode("utf-8")
        try:
            if timeout == 0:
                timout = None
            out = subprocess.run(cmd, shell=True, capture_output=True, input = input, timeout = timeout)
            retval = out.returncode, out.stdout.decode("utf-8"), out.stderr.decode("utf-8")
        except subprocess.TimeoutExpired:
            retval = CMDTIMEOUT, "", ""

        return retval

    def command(self, cmd, retcode = 0, input = None, timeout = None, timeoutError = False):
        returncode, stdout, stderr = self.runCommand(cmd, input, timeout)

        if returncode == CMDTIMEOUT and not timeoutError:
            returncode = 0
        if retcode != returncode:
            self.handleError(returncode, stderr)

        return stdout

    def commandExists(self, cmd):
        returncode, stdout, stderr = self.runCommand(cmd)

        return returncode != CMDNOTEXIST

    def handleError(self, returncode, stderr):
        exc = ("External command failed.\n"
               "Command returned: {}\n"
               "Error message:\n{}").format(returncode, stderr)
        raise Exception(exc)

#########################################################
# Class : systemdctl                                    #
#########################################################
class systemdctl(object):
    def __init__(self):
        self.hasSystemd = False
        try:
            self.hasSystemd = self.checkInstalled()
        except Exception as e:
            print("Error reading systemd information")
            print(e)
            exit(1)

    def __del__(self):
        pass

    def available(self):
        return self.hasSystemd

    def start(self, service):
        retval = False
        if self.available():
            cmd = "{} {}".format(CTLSTART, service)
            try:
                shell().command(cmd)
                retval = True
            except:
                pass
        return retval

    def stop(self, service):
        retval = False
        if self.available():
            cmd = "{} {}".format(CTLSTOP, service)
            try:
                shell().command(cmd)
                retval = True
            except:
                pass
        return retval

    def reload(self, service):
        retval = False
        if self.available():
            cmd = "{} {}".format(CTLRELOAD, service)
            try:
                shell().command(cmd)
                retval = True
            except:
                pass
        return retval

    def restart(self, service):
        retval = False
        if self.available():
            cmd = "{} {}".format(CTLRESTART, service)
            try:
                shell().command(cmd)
                retval = True
            except:
                pass
        return retval

    def enable(self, service):
        retval = False
        if self.available():
            cmd = "{} {}".format(CTLENABLE, service)
            try:
                shell().command(cmd)
                retval = True
            except:
                pass
        return retval

    def disable(self, service):
        retval = False
        if self.available():
            cmd = "{} {}".format(CTLDISABLE, service)
            try:
                shell().command(cmd)
                retval = True
            except:
                pass
        return retval

    def status(self, service):
        retval = []
        if self.available():
            cmd = "{} {}".format(CTLSTATUS, service)
            try:
                retcode, stdout, stderr = shell().runCommand(cmd)
                retval = stdout.splitlines()
            except:
                pass
        return retval

    def isActive(self, service):
        retval = False
        if self.available():
            cmd = "{} {}".format(CTLISACTIVE, service)
            try:
                shell().command(cmd)
                retval = True
            except:
                pass
        return retval

    def isEnabled(self, service):
        retval = False
        if self.available():
            cmd = "{} {}".format(CTLISENABLED, service)
            try:
                shell().command(cmd)
                retval = True
            except:
                pass
        return retval

################## INTERNAL FUNCTIONS ###################

    def checkInstalled(self):
        return shell().commandExists(SYSTEMCTL)

#########################################################
# Class : fccli                                         #
#########################################################
class fccli(object):
    def __init__(self):
        self.name = ""

    def __del__(self):
        pass

    def __str__(self):
        return "{}: commandline interface for fancontrol".format(self.name)

    def __repr__(self):
        return self.__str__()

    def run(self, argv):
        if len(os.path.split(argv[0])) > 1:
            self.name = os.path.split(argv[0])[1]
        else:
            self.name = argv[0]

        for arg in argv:
            if arg[0] == "-":
                if arg == "-h" or arg == "--help":
                    self.printHelp()
                    exit()
                elif arg == "-v" or arg == "--version":
                    print(self)
                    print("Version: {}".format(VERSION))
                    exit()
                else:
                    self.parseError(arg)
        if len(argv) < 2:
            self.lst()
        elif argv[1] == "set":
            opt = argv[1]
            if len(argv) < 3:
                opt += " <name:optional> <json options>"
                self.parseError(opt)
            if len(argv) < 4:
                self.set(argv[2])
            else:
                self.set(argv[3], fan=argv[2])
        elif argv[1] == "get":
            opt = argv[1]
            if len(argv) < 3:
                self.get()
            else:
                self.get(fan=argv[2])
        elif argv[1] == "gen":
            opt = argv[1]
            self.get(gen = True)
        elif argv[1] == "ctl":
            opt = argv[1]
            if len(argv) < 3:
                opt += " <name>"
                self.parseError(opt)
            self.ctl(argv[2])
        elif argv[1] == "fns":
            self.fns()
        elif argv[1] == "tmp":
            self.tmp()
        elif argv[1] == "rpm":
            self.rpm()
        elif argv[1] == "pwm":
            self.pwm()
        elif argv[1] == "all":
            self.all()
        elif argv[1] == "mon":
            if len(argv) < 3:
                self.mon()
            else:
                self.mon(argv[2])
        elif argv[1] == "del":
            opt = argv[1]
            if len(argv) < 3:
                opt += " <name>"
                self.parseError(opt)
            self.delfan(argv[2])
        elif argv[1] == "log":
            self.log()
        elif not self.lst(argv[1]):
            self.parseError(argv[1])

    def printHelp(self):
        print(self)
        print("Usage:")
        print("    {} {}".format(self.name, "<argument> <json options>"))
        print("    <arguments>")
        print("        set           : sets settings with <name:optional> <json options>")
        print("        get           : gets all settings <name:optional>")
        print("        gen           : gets generic settings")
        print("        del           : deletes fancontrol <name>")
        print("        ctl           : controls daemon (start, stop, enable, disable, restart,")
        print("                                         reload, isactive, isenabled)")
        print("        fns           : get available fan controls")
        print("        tmp           : get available temperature sensors")
        print("        rpm           : get available fan RPM inputs")
        print("        pwm           : get available fan PWM outputs")
        print("        all           : get all sensors and fans")
        print("        mon           : get hwmon name and path <name>")
        print("        log           : prints current fancontrol log")
        print("        <no arguments>: lists current values")
        print("")
        print("JSON options may be entered as single JSON string using full name, e.g.")
        print("{}".format(self.name), end="")
        print(" set '{\"Farenheit\": true}'")
        print("Mind the single quotes to bind the JSON string.")

    def parseError(self, opt = ""):
        print(self)
        print("Invalid option entered")
        if opt:
            print(opt)
        print("Enter '{} -h' for help".format(self.name))
        exit(1)

    def lst(self, ctrl = None):
        # current values temp, fan RPM, fan PWM, alarm
        db = datahandler()
        vals = db.monitor(ctrl)
        if vals:
            print(json.dumps(vals))
        return vals

    def set(self, opt, fan = None):
        opts = {}
        db = datahandler()
        try:
            opts = json.loads(opt)
        except:
            self.parseError("Invalid JSON format")

        try:
            dopts = {}
            if fan:
                dopts["fans"] = {}
                dopts["fans"][fan] = opts
            else:
                dopts = opts
            nr = db.getUpdate(dopts)
            if nr > -1:
                db.update(nr)
                if nr&2:
                    self.ctl("restart")
            else:
                self.parseError("Invalid settings format")
        except:
            self.parseError("Invalid settings format")

    def get(self, fan = None, gen = False):
        data = {}
        db = datahandler()
        if (gen):
            data = db()
            if "fans" in data:
                del data["fans"]
        elif fan:
            if "fans" in db():
                for lfan in db()["fans"]:
                    if lfan == fan:
                        data = db()["fans"][lfan]
        else:
            data = db()

        print(json.dumps(data))

    def fns(self):
        print(json.dumps(datahandler().getControls()))

    def tmp(self):
        print(json.dumps(datahandler().getTempSensors()))

    def rpm(self):
        print(json.dumps(datahandler().getFanInputs()))

    def pwm(self):
        print(json.dumps(datahandler().getPWMs()))

    def all(self):
        data = {}
        db = datahandler()
        data["farenheit"] = db()['farenheit']
        data["ctrls"] = db.getControls()
        data["temps"] = db.getTempSensors()
        data["rpms"] = db.getFanInputs()
        data["pwms"] = db.getPWMs()
        print(json.dumps(data))

    def mon(self, hwmon = None):
        db = datahandler()
        if hwmon == None:
            fans = db.getControls()
            if fans:
                hwmon = fans[0].split("/")[0]
        print(json.dumps(db.getHwMon(hwmon)))

    def delfan(self, ctrl = None):
        db = datahandler()
        try:
            nr = db.delCtrl(ctrl)
            if nr > 0:
                db.update(nr)
                if nr&2:
                    self.ctl("restart")
            else:
                self.parseError("Invalid fan control")
        except:
            self.parseError("Invalid fan control")

    def log(self):
        logdata = []
        origdata = shell().command("journalctl -u fancontrol --no-pager -r").split("\n")
        for origline in origdata:
            logline = {}
            log1 = origline.split("]:")
            if len(log1) > 1:
                log2 = log1[0].rsplit("[", 1)[0].rsplit(" ", 1)
                log3 = log2[0].rsplit(" ", 1)

                logline["date"]=log3[0]
                logline["app"]=log2[1]
                logline["log"]=log1[1]
                logdata.append(logline)
        print(json.dumps(logdata))

    def ctl(self, opt):
        result = {}
        sctl = systemdctl()
        if not sctl.available():
            print("Reason: systemd unavailable on your distro")
            print("{} cannot automatically restart the {} service".format(self.name, DAEMONSFC))
            print("You can try it yourself using a command like 'service {} restart'".format(DAEMONSFC))
            self.parseError()
        if opt == "start":
            result['result'] = sctl.start(DAEMONSFC)
        elif opt == "stop":
            result['result'] = sctl.stop(DAEMONSFC)
        elif opt == "restart":
            result['result'] = sctl.restart(DAEMONSFC)
        elif opt == "reload":
            result['result'] = sctl.reload(DAEMONSFC)
        elif opt == "enable":
            result['result'] = sctl.enable(DAEMONSFC)
        elif opt == "disable":
            result['result'] = sctl.disable(DAEMONSFC)
        elif opt == "isactive":
            result['result'] = sctl.isActive(DAEMONSFC)
        elif opt == "isenabled":
            result['result'] = sctl.isEnabled(DAEMONSFC)
        else:
            self.parseError("Invalid ctl option: {}".format(opt))
        print(json.dumps(result))

######################### MAIN ##########################
if __name__ == "__main__":
    fccli().run(sys.argv)
