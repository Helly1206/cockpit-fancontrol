#!/usr/bin/python3

# -*- coding: utf-8 -*-
#########################################################
# SERVICE : datahandler.py                              #
#           database and handler functions for auto-    #
#           mating fancontrol for commandline or app.   #
#           I. Helwegen 2023                            #
#########################################################

####################### IMPORTS #########################
import os
import xml.etree.ElementTree as ET
from xml.dom.minidom import parseString
#########################################################

####################### GLOBALS #########################
ETC_LOC       = "/etc"
CTRL_FILENAME = "/etc/fancontrol"
CPIT_FILENAME = "/etc/fancontrol.xml"
ENCODING      = 'utf-8'
DEF_SETTINGS  = {"farenheit": False, "logger": None, "loggerinterval": 60, "names": {}}
HWMON_FOLDER  = "/sys/class/hwmon"
SYS_FOLDER    = "/sys"
HWMON_SUB     = "hwmon"
#########################################################

###################### FUNCTIONS ########################

#########################################################
# Class : datahandler                                   #
#########################################################
class datahandler(object):
    def __init__(self):
        self.db = {}
        if not self.getPath(False):
            print("Fancontrol file not found. Please install fancontrol and run pwmconfig from command line.")
            print("pwmconfig finds fans and inputs and automatically configurate fans.")
            exit(1)
        if not self.getCpitPath(False):
            # only create xml if super user, otherwise keep empty
            self.createXML()
        self.getDataFile()

    def __del__(self):
        del self.db
        self.db = {}

    def __call__(self):
        return self.db

    def update(self, nr = 0):
        self.updateDataFile(nr)

    def getUpdate(self, opts):
        return self.findUpdate(opts)

    def delCtrl(self, ctrl):
        return self.doDel(ctrl)

    def reload(self):
        del self.db
        self.db = {}
        self.getDataFile()

    def getControls(self):
        return self.findControls()

    def monitor(self, ctrl = None):
        val = {}
        ctrls = self.getControls()
        if (not ctrl) and ctrls:
            ctrl = list(ctrls.keys())[0]
        if ctrl in ctrls:
            val['ctrl'] = ctrl
            val['farenheit'] = self.db['farenheit']
            val['temp'] = self.getMonValue(ctrl, "temp")
            val['rpm'] = self.getMonValue(ctrl, "fan")
            val['pwm'] = self.getMonValue(ctrl)
            val['alarm'] = self.getAlarms(ctrl, "temp", "fan")
        return val

    def getTempSensors(self):
        sensors = {}
        devices = self.getDevices()
        for hwmon in devices.keys():
            loc = self.getLocation("", hwmon)
            if loc:
                devlst = os.listdir(loc)
                for dev in devlst:
                    if dev.startswith("temp") and dev.endswith("_input"):
                        name = self.readDevFile(os.path.join(loc, dev.replace("_input","_label")))
                        sensors[hwmon + "/" + dev] = devices[hwmon]["devname"] + ":" + name
        return sensors

    def getFanInputs(self):
        sensors = {}
        devices = self.getDevices()
        for hwmon in devices.keys():
            loc = self.getLocation("", hwmon)
            if loc:
                devlst = os.listdir(loc)
                for dev in devlst:
                    if dev.startswith("fan") and dev.endswith("_input"):
                        sensors[hwmon + "/" + dev] = devices[hwmon]["devname"] + ":" + dev.replace("_input","")
        return sensors

    def getPWMs(self):
        sensors = {}
        devices = self.getDevices()
        for hwmon in devices.keys():
            loc = self.getLocation("", hwmon)
            if loc:
                devlst = os.listdir(loc)
                for dev in devlst:
                    if dev.startswith("pwm") and not "_" in dev:
                        sensors[hwmon + "/" + dev] = devices[hwmon]["devname"] + ":" + dev
        return sensors

    def getHwMon(self, hwmon):
        dev = {}
        devices = self.getDevices()
        if hwmon in devices.keys():
            dev = devices[hwmon] # get devPath, devName
        return dev

    def getLogger(self):
        logger = ""
        if "logger" in self.db:
            logger = self.db["logger"]
        if not logger:
            ctrls = self.getControls()
            if ctrls:
                logger = list(ctrls.keys())[0]
        return logger

    def bl(self, val):
        retval = False
        try:
            f = float(val)
            if f > 0:
                retval = True
        except:
            if val.lower() == "true" or val.lower() == "yes" or val.lower() == "1":
                retval = True
        return retval

################## INTERNAL FUNCTIONS ###################

    def gettype(self, text, txtype = True):
        try:
            retval = int(text)
        except:
            try:
                retval = float(text)
            except:
                if text:
                    if text.lower() == "false":
                        retval = False
                    elif text.lower() == "true":
                        retval = True
                    elif txtype:
                        retval = text
                    else:
                        retval = ""
                else:
                    retval = ""

        return retval

    def settype(self, element):
        retval = ""
        if type(element) == bool:
            if element:
                retval = "true"
            else:
                retval = "false"
        elif element != None:
            retval = str(element)

        return retval

    def getMonValue(self, ctrl, key = ""):
        value = 0
        loc = self.getLocation(ctrl, key)

        if loc:
            value = self.readDevFile(loc)
            if key == "temp":
                value = self.tempCalc(value/1000)
        return value

    def getAlarms(self, ctrl, temp, fan):
        alarm = "Ok"
        loc = self.getLocation(ctrl, temp)
        if loc:
            part = loc.rsplit("_", 1)[0]
            if self.getAlarm(part + "_alarm"):
                self.setAlarmText(alarm, "Temperature alarm")
            if self.getAlarm(part + "_crit_alarm"):
                self.setAlarmText(alarm, "Temperature critical")

        loc = self.getLocation(ctrl, fan)
        if loc:
            part = loc.rsplit("_", 1)[0]
            if self.getAlarm(part + "_alarm"):
                self.setAlarmText(alarm, "Fan alarm")

        return alarm

    def getAlarm(self, loc):
        value = self.readDevFile(loc)
        if not value:
            value = 0
        return value

    def setAlarmText(self, alarm, text):
        if alarm == "Ok":
            alarm = text
        else:
            alarm = alarm + " & " + text

    def getLocation(self, ctrl, key = ""):
        loc = ""
        hwmon = ""
        inp = ""

        try:
            if not ctrl:
                hwmon = key
            elif not key: #pwm location
                hwmon = ctrl.split("/", 1)[0]
                inp = ctrl.split("/", 1)[1]
            else:
                hwmon = self.db["fans"][ctrl][key].split("/", 1)[0]
                inp = self.db["fans"][ctrl][key].split("/", 1)[1]

            if os.path.exists(HWMON_FOLDER):
                loc = os.path.join(HWMON_FOLDER, hwmon, inp)
            else:
                #/sys/devices/platform/coretemp.0/hwmon/hwmon1/
                loc = os.path.join(SYS_FOLDER, self.db["devices"][hwmon]["devpath"], hwmon, inp)
        except:
            pass

        return loc

    def getDevices(self):
        devices = {}
        # do not look in /sys/bus/i2c/devices -> obsolete for 2.x kernels
        if os.path.exists(HWMON_FOLDER):
            devdirs = os.listdir(HWMON_FOLDER)
            for devdir in devdirs:
                if devdir.startswith(HWMON_SUB):
                    device = {}
                    devpath = ""
                    try:
                        lndir = os.readlink(os.path.join(HWMON_FOLDER, devdir, "device"))
                        devpath = os.path.realpath(os.path.join(HWMON_FOLDER, devdir, lndir)).replace("/sys/", "")
                    except:
                        pass
                    device["devpath"] = devpath
                    device["devname"] = self.readDevFile(os.path.join(HWMON_FOLDER, devdir, "name"))
                    devices[devdir] = device
        else: #do not search in all devices
            pass
        return devices

    def readDevFile(self, loc):
        val = ""
        try:
            with open(loc) as f:
                val = self.gettype(f.read().strip("\n"))
        except:
            pass
        return val

    def tempCalc(self, temp, inv = False):
        rtemp = temp
        if ("farenheit" in self.db) and (self.db["farenheit"]):
            if inv:
                rtemp = (temp - 32) / 1.8
            else:
                rtemp = temp * 1.8 + 32
            if int(rtemp) == rtemp:
                rtemp = int(rtemp)
        return rtemp

    def findUpdate(self, opts):
        nr = 0

        for key in opts.keys():
            if key in DEF_SETTINGS.keys():
                if self.db[key] != opts[key]:
                    nr = nr | 1
                    self.db[key] = opts[key]
            elif key == "interval":
                if self.db[key] != opts[key]:
                    nr = nr | 2
                    self.db[key] = opts[key]
            elif key == "devices":
                nr = self.findUpdateValues(opts, key, nr, ["devpath", "devname"])
            elif key == "fans":
                nr = self.findUpdateValues(opts, key, nr,
                    ["temp", "fan", "mintemp", "maxtemp", "minstart", "minstop"],
                    ["minpwm", "maxpwm"], ["name"], True)
        return nr

    def findUpdateValues(self, opts, key, nr, keys, optkeys = [], xmlkeys = [], fans = False):
        nnr = nr
        try:
            for okey in opts[key].keys():
                if okey in self.db[key].keys():
                    for ookey in opts[key][okey].keys():
                        if (ookey not in keys) and (ookey not in optkeys) and (ookey not in xmlkeys):
                            nnr = -1
                            break
                        else:
                            if (ookey in xmlkeys):
                                nnr = nnr | 1
                            else:
                                nnr = nnr | 2
                            if (ookey in optkeys) and (opts[key][okey][ookey] == None):
                                del self.db[key][okey][ookey]
                            else:
                                self.db[key][okey][ookey] = opts[key][okey][ookey]
                else: #new key
                    kdb = {}
                    for reqkey in keys:
                        if not reqkey in opts[key][okey].keys():
                            nnr = -1
                            break
                        else:
                            kdb[reqkey] = opts[key][okey][reqkey]
                            nnr = nnr | 2
                    for xmlkey in xmlkeys:
                        if not xmlkey in opts[key][okey].keys():
                            nnr = -1
                            break
                        else:
                            kdb[xmlkey] = opts[key][okey][xmlkey]
                            nnr = nnr | 1
                    for optkey in optkeys:
                        if optkey in opts[key][okey].keys():
                            kdb[optkey] = opts[key][okey][optkey]
                            nnr = nnr | 2
                    self.db[key][okey] = kdb
                    if fans:
                        hwmon = okey.split("/", 1)[0]
                        if not hwmon in self.db["devices"].keys():
                            self.db["devices"][hwmon]=self.getHwMon(hwmon)
        except:
            nnr = -1
        return nnr

    def doDel(self, ctrl):
        nnr = 0
        if "fans" in self.db:
            if ctrl in self.db["fans"]:
                if "name" in self.db["fans"][ctrl] and self.db["fans"][ctrl]["name"]:
                    nnr = nnr | 1
                del self.db["fans"][ctrl]
                nnr = nnr | 2
        return nnr

    def findControls(self):
        fans = []
        ctrls = {}
        if "fans" in self.db:
            fans = list(self.db["fans"].keys())
        for fan in fans:
            ctrl = {}
            hwmon = fan.split("/")[0]
            devices = self.getDevices()
            ctrl["device"] = ""
            if hwmon in devices.keys():
                ctrl["device"] = devices[hwmon]["devname"]
            ctrl["name"] = ""
            if "name" in self.db["fans"][fan] and self.db["fans"][fan]["name"]:
                ctrl["name"] = self.db["fans"][fan]["name"]
            else:
                ctrl["name"] = ctrl["device"] + ":" + fan
            ctrl["default"] = False
            if "logger" in self.db:
                if self.db["logger"] == fan:
                    ctrl["default"] = True
            ctrls[fan] = ctrl
        return ctrls

    def getDataFile(self):
        self.db = self.getXML()
        self.db.update(self.getCtrlFile())
        self.addNames(self.db)

    def getXML(self):
        db = {}
        XMLpath = self.getCpitPath()
        try:
            tree = ET.parse(XMLpath)
            root = tree.getroot()
            db = self.parseKids(root)
        except Exception as e:
            self.logger.error("Error parsing xml file")
            self.logger.error("Check XML file syntax for errors")
            self.logger.exception(e)
            exit(1)
        return db

    def getCtrlFile(self):
        FilePath = self.getPath()
        db = {}
        try:
            with open(FilePath) as f:
                while True:
                    line = f.readline().strip()
                    if not line:
                        break
                    self.parseLine(line, db)

        except Exception as e:
            print("Error parsing fancontrol file")
            print("Check fancontrol file syntax for errors")
            print(e)
            exit(1)
        return db

    def addNames(self, db):
        if "fans" in db:
            for fan in db["fans"].keys():
                fan1 = fan.replace("/", "_")
                name = ""
                if "names" in db:
                    if fan1 in db["names"]:
                        name = db["names"][fan1]
                db["fans"][fan]["name"] = name
        if "names" in db:
            del db["names"]

    def parseLine(self, line, db):
        val = self.getValue(line, "INTERVAL")
        if val:
            db["interval"] = int(val)
        elif not "interval" in db:
            db["interval"] = 0
        if not "devices" in db:
            db["devices"] = {}
        val = self.getValue(line, "DEVPATH")
        if val:
            self.splitValues(val, db["devices"], "devpath")
        val = self.getValue(line, "DEVNAME")
        if val:
            self.splitValues(val, db["devices"], "devname")
        if not "fans" in db:
            db["fans"] = {}
        val = self.getValue(line, "FCTEMPS")
        if val:
            self.splitValues(val, db["fans"], "temp")
        val = self.getValue(line, "FCFANS")
        if val:
            self.splitValues(val, db["fans"], "fan")
        val = self.getValue(line, "MINTEMP")
        if val:
            self.splitValues(val, db["fans"], "mintemp", True)
        val = self.getValue(line, "MAXTEMP")
        if val:
            self.splitValues(val, db["fans"], "maxtemp", True)
        val = self.getValue(line, "MINSTART")
        if val:
            self.splitValues(val, db["fans"], "minstart")
        val = self.getValue(line, "MINSTOP")
        if val:
            self.splitValues(val, db["fans"], "minstop")
        val = self.getValue(line, "MINPWM")
        if val:
            self.splitValues(val, db["fans"], "minpwm")
        val = self.getValue(line, "MAXPWM")
        if val:
            self.splitValues(val, db["fans"], "maxpwm")

    def getValue(self, line, param):
        val = ""
        param += "="
        if line.startswith(param):
            val = line.replace(param, "")
        return val

    def splitValues(self, vals, dbx, param, temp = False):
        for val in vals.strip().split():
            kval = self.splitKeyVal(val)
            if not kval[0] in dbx:
                dbx[kval[0]] = {}
            rv = self.gettype(kval[1])
            if temp:
                rv = self.tempCalc(rv)
            dbx[kval[0]].update({ param: rv })

    def splitKeyVal(self, val):
        kval = val.split("=")
        if len(kval) < 2:
            kval.insert(0, "")
        return kval

    def updateDataFile(self, nr):
        if (nr & 1):
            self.getNames(self.db)
            self.updateXML()
        if (nr & 2):
            self.updateCtrlFile()

    def getNames(self, db):
        names = {}

        if "fans" in db:
            for fan in db["fans"].keys():
                fan1 = fan.replace("/", "_")
                name = ""
                if "name" in db["fans"][fan] and db["fans"][fan]["name"]:
                    names[fan1] = db["fans"][fan]["name"]
        db["names"]=names


    def updateCtrlFile(self):
        lines = self.getComment()

        self.buildLine(self.db, lines, "interval", "INTERVAL")
        if "devices" in self.db:
            self.buildLineMulti(self.db["devices"], lines, "devpath", "DEVPATH")
            self.buildLineMulti(self.db["devices"], lines, "devname", "DEVNAME")
        if "fans" in self.db:
            self.buildLineMulti(self.db["fans"], lines, "temp", "FCTEMPS")
            self.buildLineMulti(self.db["fans"], lines, "fan", "FCFANS")
            self.buildLineMulti(self.db["fans"], lines, "mintemp", "MINTEMP", True)
            self.buildLineMulti(self.db["fans"], lines, "maxtemp", "MAXTEMP", True)
            self.buildLineMulti(self.db["fans"], lines, "minstart", "MINSTART")
            self.buildLineMulti(self.db["fans"], lines, "minstop", "MINSTOP")
            self.buildLineMulti(self.db["fans"], lines, "minpwm", "MINPWM")
            self.buildLineMulti(self.db["fans"], lines, "maxpwm", "MAXPWM")

        FilePath = self.getPath(dowrite = True)

        with open(FilePath, "w") as f:
            f.writelines(line + '\n' for line in lines)

    def buildLine(self, db, lines, key, param):
        if key in db:
            line = param + "=" + self.settype(db[key])
            lines.append(line)

    def buildLineMulti(self, db, lines, key, param, temp = False):
        multiLines = []
        for device, val in db.items():
            if key in val:
                rv = val[key]
                if temp:
                    try:
                        float(rv)
                        rv = self.tempCalc(rv, True)
                    except:
                        pass
                multiLines.append(device + "=" + self.settype(rv))
        if len(multiLines) > 0:
            line = param + "=" + " ".join(multiLines)
            lines.append(line)

    def getComment(self):
        comment = []
        FilePath = self.getPath()
        db = {}
        try:
            with open(FilePath) as f:
                while True:
                    line = f.readline().strip()
                    if not line:
                        break
                    if line.startswith("#"):
                        comment.append(line)

        except Exception as e:
            print("Error parsing fancontrol file")
            print("Check fancontrol file syntax for errors")
            print(e)
            exit(1)
        return comment

    def parseKids(self, item):
        db = {}
        if self.hasKids(item):
            for kid in item:
                if self.hasKids(kid):
                    db[kid.tag] = self.parseKids(kid)
                else:
                    db.update(self.parseKids(kid))
        else:
            db[item.tag] = self.gettype(item.text)
        return db

    def hasKids(self, item):
        retval = False
        for kid in item:
            retval = True
            break
        return retval

    def updateXML(self):
        XMLpath = self.getCpitPath(dowrite = True)
        db = ET.Element('settings')
        comment = ET.Comment(self.getXMLcomment("settings"))
        db.append(comment)
        resdb = {key: self.db[key] for key in self.db.keys() if key in DEF_SETTINGS.keys()}
        self.buildXML(db, resdb)
        with open(XMLpath, "w") as xml_file:
            xml_file.write(self.prettify(db))

    def buildXML(self, xmltree, item):
        if isinstance(item, dict):
            for key, value in item.items():
                kid = ET.SubElement(xmltree, key)
                self.buildXML(kid, value)
        else:
            xmltree.text = self.settype(item)

    def createXML(self):
        #print("Creating new XML file")
        XMLpath = CPIT_FILENAME
        self.checkEtcWritable()
        db = ET.Element('settings')
        comment = ET.Comment("This XML file describes the fancontrol configuration.\n"
        "            This file is managed by cockpit-fancontrol, edit at your own risk.")
        db.append(comment)
        settings = DEF_SETTINGS
        self.buildXML(db, settings)
        with open(XMLpath, "w") as xml_file:
            xml_file.write(self.prettify(db))

    def getXMLcomment(self, tag):
        comment = ""
        XMLpath = self.getCpitPath()
        with open(XMLpath, 'r') as xml_file:
            content = xml_file.read()
            xmltag = "<{}>".format(tag)
            xmlend = "</{}>".format(tag)
            begin = content.find(xmltag)
            end = content.find(xmlend)
            content = content[begin:end]
            cmttag = "<!--"
            cmtend = "-->"
            begin = content.find(cmttag)
            end = content.find(cmtend)
            if (begin > -1) and (end > -1):
                comment = content[begin+len(cmttag):end]
        return comment

    def prettify(self, elem):
        """Return a pretty-printed XML string for the Element.
        """
        rough_string = ET.tostring(elem, ENCODING)
        reparsed = parseString(rough_string)
        return reparsed.toprettyxml(indent="\t").replace('<?xml version="1.0" ?>','<?xml version="1.0" encoding="%s"?>' % ENCODING)


    def getPath(self, doexit = True, dowrite = False):
        retPath = ""
        # first look in etc
        if os.path.isfile(CTRL_FILENAME):
            retPath = CTRL_FILENAME
            if dowrite and not os.access(CTRL_FILENAME, os.W_OK):
                print("No valid writable file location found")
                print("File cannot be written, please run as super user")
                if doexit:
                    exit(1)
        else: # Only allow etc location
            print("No file found: {}".format(CTRL_FILENAME))
            if doexit:
                exit(1)
        return retPath

    def getCpitPath(self, doexit = True, dowrite = False):
        retPath = ""
        # first look in etc
        if os.path.isfile(CPIT_FILENAME):
            retPath = CPIT_FILENAME
            if dowrite and not os.access(CPIT_FILENAME, os.W_OK):
                print("No valid writable file location found")
                print("File cannot be written, please run as super user")
                if doexit:
                    exit(1)
        else: # Only allow etc location
            print("No file found: {}".format(CPIT_FILENAME))
            if doexit:
                exit(1)
        return retPath

    def checkEtcWritable(self, doexit = True):
        if not os.access(ETC_LOC, os.W_OK):
            print("No valid writable file location found")
            print("File cannot be created, please run as super user")
            if doexit:
                exit(1)

#########################################################
