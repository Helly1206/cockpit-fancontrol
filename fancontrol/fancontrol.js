/*********************************************************
 * SCRIPT : fancontrol.js                                *
 *          Javascript for fancontrol Cockpit web-gui    *
 *          Based on SmartFanControl for RPi             *
 *          I. Helwegen 2023                             *
 *********************************************************/

////////////////////
// Common classes //
////////////////////

class fcMonitor {
    constructor(el) {
        this.el = el;
        this.name = "monitor";
        this.startButton = null;
        this.stopButton = null;
        this.pane = new tabPane(this, el, this.name);
        this.refresh = 1000;
        this.ctrl = "";
    }

    displayContent(el) {
        this.displayMonitor();
    }

    displayMonitor(text = "") {
        this.pane.dispose();
        this.pane.build(text, true);
        this.pane.getTitle().innerHTML = this.name.charAt(0).toUpperCase() + this.name.slice(1);
        this.displayButtons(true);
        this.setTimer();
        this.getSettings();
    }

    displayGraph(text = "") {
        this.pane.dispose();
        this.pane.build(text, false, true);
        //this.pane.getTitle().innerHTML = this.name.charAt(0).toUpperCase() + this.name.slice(1) + " - Graph";
        this.displayButtons(false);
        this.getData();
    }

    getSettings(callback) {
        var cb = function(data) {
            var fData = JSON.parse(data);
            var scb = function(idata) {
                var iData = JSON.parse(idata);
                this.buildEditForm(iData, fData);
            }
            this.ctrl = this.getCtrl(fData);
            runCmd.call(this, scb, [this.ctrl]);
        }
        this.update = {};
        runCmd.call(this, cb, ["fns"]);
    }

    displayButtons(grp = true) {
        var cb = function(data, status) {
            var running = (status == 0);
            if (grp) {
                this.pane.addButton("graph", "Log graph", this.displayGraph, true, false, false);
            } else {
                this.pane.addButton("monitor", "Monitor", this.displayMonitor, true, false, false);
                this.pane.addButton("refresh", "Refresh", this.displayGraph, false, false, false);
            }
            this.startButton = this.pane.addButton("start", "Start logging", this.startLogging, false, running, false);
            this.stopButton = this.pane.addButton("stop", "Stop logging", this.stopLogging, false, !running, false);
        }
        this.update = {};
        runLog.call(this, cb, "status");
    }

    refreshSettings(callback) {
        var cb = function(data) {
            var iData = JSON.parse(data);
            //var form = this.pane.getSettingsEditForm();
            this.pane.getSettingsEditForm().updateData([{
                param: "temp",
                value: iData.temp
            }, {
                param: "rpm",
                value: iData.rpm
            }, {
                param: "pwm",
                value: iData.pwm
            }, {
                param: "alarm",
                value: iData.alarm
            }]);
        }
        this.update = {};
        runCmd.call(this, cb, [this.ctrl]);
    }

    setTimer() {
        var onTimer = function() {
            if (this.el.classList.contains("active")) {
                this.refreshSettings();
            } else {
                this.clearTimer();
            }
        };
        if (this.timer == null) {
            this.timer = setInterval(onTimer.bind(this), this.refresh);
        }
    }

    clearTimer() {
        if (this.timer != null) {
            clearInterval(this.timer);
            this.timer = null;
        }
    }

    buildEditForm(aData, fData) {
        var ctrlOpts = [];
        var ctrlLabels = [];
        var ctrlReadOnly = true;
        var ctrlDefault = "";
        var nfans = Object.keys(fData).length;
        if (nfans > 0) {
            Object.keys(fData).forEach(key => {
                ctrlOpts.push(fData[key].name);
                ctrlLabels.push(key);
                if (fData[key].default) {
                    ctrlDefault = fData[key].name;
                }
            });
            if (!ctrlDefault) {
                ctrlDefault = ctrlOpts[0];
            }
            if (nfans > 1) {
                ctrlReadOnly = false;
            }
        } else {
            new msgBox(this, "No valid fans found", "Please add fans first");
            return;
        }
        var ctrlChangedCallback = function(param, ctrl) {
            this.ctrl = ctrl;
        };
        var tempUnit = "&#176;C";
        if (aData.farenheit) {
            tempUnit = "&#176;F";
        }
        //{"temp": -1, "fan": -1, "alarm": "Ok"}
        var dlgData = [{
                param: "ctrl",
                text: "Fan control",
                value: ctrlDefault,
                type: "select",
                opts: ctrlOpts,
                optslabel: ctrlLabels,
                labelvalue: true,
                displaylabel: false,
                disabled: false,
                readonly: ctrlReadOnly,
                onchange: ctrlChangedCallback,
                comment: "Fan control to monitor (see settings for logger)"
            },{
                param: "temp",
                text: "Temperature [" + tempUnit + "]",
                value: aData.temp,
                type: "number",
                disabled: false,
                readonly: true,
                comment: "Current system temperature in " + tempUnit + "."
            }, {
                param: "rpm",
                text: "Fan speed [RPM]",
                value: aData.rpm,
                type: "number",
                disabled: false,
                readonly: true,
                comment: "Current fan speed in RPM."
            }, {
                param: "pwm",
                text: "Fan control [PWM]",
                value: aData.pwm,
                type: "number",
                disabled: false,
                readonly: true,
                comment: "Current fan control in PWM."
            }, {
                param: "alarm",
                text: "Alarm",
                value: aData.alarm,
                type: "text",
                disabled: false,
                readonly: true,
                comment: "Current alarm status."
            }
        ];
        this.pane.getSettingsEditForm().setData(dlgData);
    }

    startLogging() {
        var cb = function(data, status) {
            if (status == 0) {
                if ((this.startButton) && (this.stopButton)) {
                    this.pane.setButtonDisabled(this.startButton, true);
                    this.pane.setButtonDisabled(this.stopButton, false);
                }
            }
        }
        this.update = {};
        runLog.call(this, cb, "start");
    }

    stopLogging() {
        var cb = function(data, status) {
            if (status == 0) {
                if ((this.startButton) && (this.stopButton)) {
                    this.pane.setButtonDisabled(this.startButton, false);
                    this.pane.setButtonDisabled(this.stopButton, true);
                }
            }
        }
        this.update = {};
        runLog.call(this, cb, "stop");
    }

    getData() {
        var cb = function(data, status) {
            if (status == 0) {
                var iData = JSON.parse(data);
                this.buildGraph(iData);
            }
        }
        this.update = {};
        runLog.call(this, cb);
    }

    buildGraph(iData) {
        var tempText = "Temperature []";
        var ctrlText = "Fan speed [RPM]";
        var lData = this.processData(iData);
        var graphName = "";
        if ('settings' in iData) {
            if ('farenheit' in iData.settings) {
                if (iData.settings.farenheit) {
                    tempText = "Temperature [°F]";
                } else {
                    tempText = "Temperature [°C]";
                }
            }
            if ('fancontrol' in iData.settings) {
                if (iData.settings.fancontrol) {
                    graphName = " (" + iData.settings.fancontrol + ")";
                }
            }
        }
        this.pane.getTitle().innerHTML = this.name.charAt(0).toUpperCase() + this.name.slice(1) + " - Graph" + graphName;
        const data = {
            labels: lData.time,
            datasets: [{
                label: tempText,
                yAxisID: 'temp',
                backgroundColor: 'rgb(255, 99, 132)',
                borderColor: 'rgb(255, 99, 132)',
                data: lData.temp
            }, {
                label: ctrlText,
                yAxisID: 'ctrl',
                backgroundColor: 'rgb(70,130,180)',
                borderColor: 'rgb(70,130,180)',
                data: lData.ctrl
            }]
        };
        const config = {
            type: 'line',
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: true,
                aspectRatio: 2.5,
                scales: {
                    x: {
                        type: 'linear',
                            min: lData.scale.min,
                            max: lData.scale.max,
                            ticks: {
                                stepSize: lData.scale.step
                            },
                        title: {
                            display: true,
                            text: 'time [min]'
                        }
                    },
                    temp: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: tempText
                        }
                    },
                    ctrl: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: ctrlText
                        },
                        grid: {
                            drawOnChartArea: false, // only want the grid lines for one axis to show up
                        }
                    }
                }
            }
        };
        this.pane.getCanvas().setData();
        var myChart = new Chart(this.pane.getCanvas().getCanvas(), config);
    }

    processData(iData) {
        var tmStart = 0;
        var tmMax = 0;
        var lData = {};
        var timeScale = {};
        var timeData = [];
        var tempData = [];
        var ctrlData = [];
        var first = true;

        if ('data' in iData) {
            iData.data.forEach(datum => {
                if ('time' in datum) {
                    let tmCur = parseInt(datum.time);
                    if (first) {
                        tmStart = tmCur;
                        tmMax = 0;
                        timeData.push(0);
                        first = false;
                    } else {
                        let tmVal = Math.trunc((tmCur-tmStart)/60);
                        if (tmVal > tmMax) {
                            tmMax = tmVal;
                        }
                        timeData.push(tmVal);
                    }
                }
                if ('temp' in datum) {
                    tempData.push(parseFloat(datum.temp));
                }
                if ('rpm' in datum) {
                    ctrlData.push(parseFloat(datum.rpm));
                }
                /*if ('pwm' in datum) {
                    ctrlData.push(parseFloat(datum.pwm));
                }*/
            });
        }
        timeScale.min = 0;
        timeScale.max = tmMax;
        timeScale.step = 1;
        if (timeScale.max-timeScale.min > 10) {
            timeScale.step = Math.round((timeScale.max-timeScale.min)/10);
        }
        lData.scale = timeScale;
        lData.time = timeData;
        lData.temp = tempData;
        lData.ctrl = ctrlData;

        return lData;
    }

    getCtrl(fData) {
        var ctrl = "";
        var ctrlOpts = [];
        var nfans = Object.keys(fData).length;
        if (nfans > 0) {
            ctrlOpts = Object.keys(fData);
            ctrlOpts.forEach(key => {
                if (fData[key].default) {
                    ctrl = key;
                }
            });
            if (!ctrl) {
                ctrl = ctrlOpts[0];
            }
        }
        return ctrl;
    }
}

class fcFans {
    constructor(el) {
        this.el = el;
        this.name = "fans settings";
        this.pane = new tabPane(this, el, this.name);
        this.dropdownContent = [
            {name : "Delete", disable: null, disableValue: null, callback: this.delete}
        ];
        this.fans = [];
    }

    displayContent(el) {
        this.pane.dispose();
        this.pane.build();
        this.pane.getTitle().innerHTML = this.name.charAt(0).toUpperCase() + this.name.slice(1);
        this.pane.addButton("add", "Add", this.tableClickCallback, true, false, false);
        //this.pane.addButton("restart", "Restart", this.displayList, false, false, false); // auto done, rest can be done in services
        this.pane.getTable().setOnClick(this.tableClickCallback);
        this.pane.getTable().setDropDown(this.dropdownContent);
        this.getFans();
    }

    getFans() {
        var cb = function(data) {
            var tData = JSON.parse(data);
            var lData = [];
            this.fans = [];
            Object.keys(tData).forEach(datum => {
                let fan = {};
                fan["Friendly name"] = tData[datum].name;
                fan.name = datum;
                fan.device = tData[datum].device;
                fan.logger = tData[datum].default;
                this.fans.push(fan);
            });
            this.pane.getTable().setData(this.fans);
        }
        runCmd.call(this, cb, "fns");
    }

    addFan(aData) {
        var fData = {};
        fData.name = "";
        fData.fan = "";
        fData.temp = "";
        fData.mintemp = 45;
        fData.maxtemp = 60;
        fData.minstart = 50;
        fData.minstop = 30;
        fData.minpwm = 0;
        fData.maxpwm = 255;

        this.pane.getTable().loadingDone();
        this.pane.disposeSpinner();
        this.buildEditDialog(null, aData, fData);
    }

    getFan(ctrlPwm, aData) {
        var cbGet = function(jData) {
            var fData = JSON.parse(jData);
            if (!("minpwm" in fData)) {
                fData.minpwm = 0;
            }
            if (!("maxpwm" in fData)) {
                fData.maxpwm = 255;
            }
            this.pane.getTable().loadingDone();
            this.pane.disposeSpinner();
            this.buildEditDialog(ctrlPwm, aData, fData);
        }
        runCmd.call(this, cbGet, ["get", ctrlPwm]);
    }

    tableClickCallback(data = null) {
        var cbAll = function(jData) {
            var aData = JSON.parse(jData);
            if (!data) {
                this.addFan(aData);
            } else {
                this.getFan(data.name, aData);
            }
        }
        this.pane.showSpinner();
        runCmd.call(this, cbAll, ["all"]);
    }

    buildEditDialog(ctrlPwm, aData, fData) {
        var tempOpts = [];
        var tempLabels = [];
        var defTemp = "";
        var pwmOpts = [];
        var pwmLabels = [];
        var defPwm = "";
        var rpmOpts = [];
        var rpmLabels = [];
        var defRpm = "";
        var tempUnit = "&#176;C";
        var farenheit = aData.farenheit;
        if (farenheit) {
            tempUnit = "&#176;F";
        }
        var sortedKeys = Object.keys(aData.temps).sort();
        sortedKeys.forEach(key => {
            tempOpts.push(aData.temps[key]);
            tempLabels.push(key);
        });
        if (tempLabels.includes(fData.temp)) {
            defTemp = aData.temps[fData.temp];
        } else {
            defTemp = tempOpts[0];
        }
        sortedKeys = this.availablePwms(Object.keys(aData.pwms).sort(), aData, ctrlPwm);
        sortedKeys.forEach(key => {
            pwmOpts.push(aData.pwms[key]);
            pwmLabels.push(key);
        });
        if (pwmLabels.includes(ctrlPwm)) {
            defPwm = aData.pwms[ctrlPwm];
        } else {
            defPwm = pwmOpts[0];
        }

        sortedKeys = Object.keys(aData.rpms).sort();
        sortedKeys.forEach(key => {
            rpmOpts.push(aData.rpms[key]);
            rpmLabels.push(key);
        });
        if (rpmLabels.includes(fData.fan)) {
            defRpm = aData.rpms[fData.fan];
        } else {
            let keyRpm = this.getRpm(aData, pwmLabels[0]);
            if (keyRpm) {
                defRpm = aData.rpms[keyRpm];
            } else {
                defRpm = rpmOpts[0];
            }
        }

        var pwmChangedCallback = function(param, pwm) {
            var keyRpm = this.getRpm(aData, pwm);
            if (keyRpm) {
                dialog.updateData([{
                    param: "fan",
                    value: aData.rpms[keyRpm]
                }]);
            }
        };
        var dlgData = [{
                param: "warning",
                text: "Caution",
                value: "Edit settings at own risk!",
                type: "text",
                readonly: true,
                comment: "Preferably use pwmconfig on commandline to setup fans."
            }, {
                param: "name",
                text: "Friendly name",
                value: fData.name,
                type: "text",
                disabled: false,
                readonly: false,
                comment: "Enter a friendly name for this fan"
            }, {
                param: "pwm",
                text: "Fan PWM control",
                value: defPwm,
                type: "select",
                opts: pwmOpts,
                optslabel: pwmLabels,
                labelvalue: true,
                disabled: false,
                readonly: false,
                onchange: pwmChangedCallback,
                comment: "Select fan PWM control to use"
            }, {
                param: "fan",
                text: "Fan RPM input",
                value: defRpm,
                type: "select",
                opts: rpmOpts,
                optslabel: rpmLabels,
                labelvalue: true,
                disabled: false,
                readonly: false,
                comment: "Select fan RPM input to use"
            }, {
                param: "temp",
                text: "Temperature input",
                value: defTemp,
                type: "select",
                opts: tempOpts,
                optslabel: tempLabels,
                labelvalue: true,
                disabled: false,
                readonly: false,
                comment: "Select temperature input to use for fan control"
            }, {
                param: "mintemp",
                text: "Minimum temperature [" + tempUnit + "]",
                value: fData.mintemp,
                type: "number",
                min: 0,
                max: 250,
                step: 1,
                disabled: false,
                readonly: false,
                comment: "The temperature below which the fan gets switched to minimum speed."
            }, {
                param: "maxtemp",
                text: "Maximum temperature [" + tempUnit + "]",
                value: fData.maxtemp,
                type: "number",
                min: 0,
                max: 250,
                step: 1,
                disabled: false,
                readonly: false,
                comment: "The temperature over which the fan gets switched to maximum speed."
            }, {
                param: "minstart",
                text: "Minimum start PWM",
                value: fData.minstart,
                type: "number",
                min: 0,
                max: 255,
                step: 1,
                disabled: false,
                readonly: false,
                comment: "Sets the minimum speed at which the fan begins spinning. " +
                         "You should use a safe value to be sure it works, even when the fan gets old."
            }, {
                param: "minstop",
                text: "Minimum stop PWM",
                value: fData.minstop,
                type: "number",
                min: 0,
                max: 255,
                step: 1,
                disabled: false,
                readonly: false,
                comment: "The minimum speed at which the fan still spins. Use a safe value here, too."
            }, {
                param: "minpwm",
                text: "Minimum PWM",
                value: fData.minpwm,
                type: "number",
                min: 0,
                max: 255,
                step: 1,
                disabled: false,
                readonly: false,
                comment: "The PWM value to use when the temperature is below mintemp. Typically, this will be either 0 if it is OK " +
                         "for the fan to plain stop, or the same value as minstop if you don't want the fan to ever stop. " +
                         "Default = 0 (stopped fan)."
            }, {
                param: "maxpwm",
                text: "Maximum PWM",
                value: fData.maxpwm,
                type: "number",
                min: 0,
                max: 255,
                step: 1,
                disabled: false,
                readonly: false,
                comment: "The PWM value to use when the temperature is over MAXTEMP. Default = 255 (full speed)."
            }
        ];
        var title = "";
        if (ctrlPwm == null) {
            title = "Add fan";
        } else {
            if (Object.keys(aData.ctrls).includes(ctrlPwm)) {
                title = "Edit fan: " + aData.ctrls[ctrlPwm].name + " [" + ctrlPwm + "]";
            } else {
                title = "Edit fan: " + ctrlPwm;
            }
        }
        var dialog = new editDialog(this);
        var cbOk = function(rData) {
            this.addEdit(rData, ctrlPwm, fData, aData);
        }
        dialog.build(title, dlgData, cbOk);
    }

    checkNameExisting(name, aData, ctrlPwm = null) {
        var rv = false;
        var used = Object.keys(aData.ctrls);
        used.forEach(key => {
            if ((ctrlPwm == null) || ((ctrlPwm != null) && (key != ctrlPwm))) {
                if (aData.ctrls[key].name == name) {
                    rv = true;
                }
            }
        });
        return rv;
    }

    addEdit(data, ctrlPwm, fData, aData) {
        var opts = [];
        if (ctrlPwm == null) {
            fData = {};
        }
        opts = buildOpts(data, fData, ["pwm"]);
        if (data.pwm) {
            var name = data.name + " [" + data.pwm + "]";
            if (this.checkNameExisting(data.name, aData, ctrlPwm)) {
                new msgBox(this, "Existing fan name " + name, "Please enter a unique name for the fan");
            } else if (Object.keys(opts).length == 0) {
                new msgBox(this, "No changes to fan", "fan not edited");
            } else {
                var cbYes = function() {
                    this.pane.showSpinner("Adding/ editing...");
                    runCmd.call(this, this.displayContent, ["set", data.pwm], opts);
                };
                var txt = "";
                if (ctrlPwm == null) {
                    txt = "Are you sure to add " + name + " as fan?";
                } else {
                    txt = "Are you sure to edit " + name + " as fan?";
                }
                new confirmDialog(this, "Add/ edit fan " + name, txt, cbYes);
            }
        } else {
            new msgBox(this, "Empty fan", "Please enter a valid name for the fan");
        }
    }

    availablePwms(pwms, aData, ctrlPwm = "") {
        var rv = [];
        var used = Object.keys(aData.ctrls);
        pwms.forEach(key => {
            if ((!(used.includes(key))) || (key == ctrlPwm)) {
                rv.push(key);
            }
        });
        return rv;
    }

    getRpm(aData, pwm) {
        var rpm = "";
        var splitpwm = pwm.split("/");
        if (splitpwm.length > 0) {
            var hwmon = splitpwm[0];
            var nr = splitpwm[splitpwm.length-1].replace(/[^0-9]/g, '');
            var fans = Object.keys(aData.rpms);
            fans.forEach(fan => {
                var splitfan = fan.split("/");
                if (splitfan.length > 0) {
                    var fanhwmon = splitfan[0];
                    var splitfan2 = splitfan[splitfan.length-1].split("_");
                    if (splitfan2.length > 0) {
                        var fannr = splitfan2[0].replace(/[^0-9]/g, '');
                        if ((fannr == nr) && (fanhwmon == hwmon)) {
                            rpm = fan;
                        }
                    }
                }
            });
        }
        return rpm;
    }

    delete(data) {
        var cbYes = function() {
            this.pane.showSpinner("Deleting...");
            runCmd.call(this, this.getFans, ["del", data.name]);
        };
        var txt = "Are you sure to delete " + data["Friendly name"] + " [" + data.name + "]?" + "<br>" +
                    "This item will be deleted from database!";
        new confirmDialog(this, "Delete " + data["Friendly name"], txt, cbYes);
    }
}

class fcSettings {
    constructor(el) {
        this.el = el;
        this.name = "settings";
        this.pane = new tabPane(this, el, this.name);
        this.update = {};
        this.btnUpdate = null;
    }

    displayContent(el) {
        this.displaySettings();
        this.getSettings();
    }

    displaySettings(text = "") {
        this.pane.dispose();
        this.pane.build(text, true);
        this.pane.getTitle().innerHTML = this.name.charAt(0).toUpperCase() + this.name.slice(1);
        this.btnUpdate = this.pane.addButton("Update", "Update", this.btnUpdateCallback, true, (Object.keys(this.update).length == 0), false);
    }

    getSettings(callback) {
        var cb = function(data) {
            var fData = JSON.parse(data);
            var scb = function(idata) {
                this.pane.setButtonDisabled(this.btnUpdate, (Object.keys(this.update).length == 0));
                var iData = JSON.parse(idata);
                this.buildEditForm(iData, fData);
            }
            runCmd.call(this, scb, ["gen"]);
        }
        this.update = {};
        runCmd.call(this, cb, ["fns"]);
    }

    buildEditForm(aData, fData) {
        var ctrlOpts = [];
        var ctrlLabels = [];
        var ctrlDefault = "";
        var nfans = Object.keys(fData).length;
        if (nfans > 0) {
            Object.keys(fData).forEach(key => {
                ctrlOpts.push(fData[key].name);
                ctrlLabels.push(key);
                if (fData[key].default) {
                    ctrlDefault = fData[key].name;
                }
            });
            if (!ctrlDefault) {
                ctrlDefault = ctrlOpts[0];
                this.update = {};
                this.update.logger = Object.keys(fData)[0];
                this.pane.setButtonDisabled(this.btnUpdate, (Object.keys(this.update).length == 0));
            }
        } else {
            new msgBox(this, "No valid fans found", "Please add fans first");
            return;
        }
        var settingsCallback = function(param, value) {
            var editData = this.pane.getSettingsEditForm().getData();
            this.update = buildOpts(editData, aData);
            this.pane.setButtonDisabled(this.btnUpdate, (Object.keys(this.update).length == 0));
        }
        var dlgData = [{
                param: "logger",
                text: "Fan control name",
                value: ctrlDefault,
                type: "select",
                opts: ctrlOpts,
                optslabel: ctrlLabels,
                labelvalue: true,
                disabled: false,
                readonly: false,
                onchange: settingsCallback,
                comment: "Fan control as default for monitor and logger"
            }, {
                param: "loggerinterval",
                text: "Logger interval [s]",
                value: aData.loggerinterval,
                type: "number",
                min: 0,
                max: 86400,
                step: 1,
                onchange: settingsCallback,
                disabled: false,
                readonly: false,
                comment: "Defines the interval between log samples in seconds. (default = 60 seconds)"
            }, {
                param: "farenheit",
                text: "Farenheit",
                value: aData.farenheit,
                type: "boolean",
                onchange: settingsCallback,
                disabled: false,
                readonly: false,
                comment: "Display the temperature in &#176;F. Default is false (temperature is displayed in &#176;C)."
            }, {
                param: "interval",
                text: "Control interval [s]",
                value: aData.interval,
                type: "number",
                min: 0,
                max: 60,
                step: 1,
                onchange: settingsCallback,
                disabled: false,
                readonly: false,
                comment: "Defines the interval for the fan controller. (default = 10 seconds)"
            }
        ];
        this.pane.getSettingsEditForm().setData(dlgData);
    }

    btnUpdateCallback() {
        var cbYes = function() {
            this.pane.dispose();
            this.displaySettings("Updating settings...");
            runCmd.call(this, this.getSettings, ['set'], this.update);
        };
        if (Object.keys(this.update).length > 0) {
            var txt = "Are you sure to update settings?"
            if ("interval" in this.update) {
                txt = "Are you sure to update settings and restart fancontrol services?"
            }
            new confirmDialog(this, "Update settings", txt, cbYes);
        } else {
            new msgBox(this, "No settings changed", "No update required!");
        }
    }
}

/////////////////////
// Common functions //
//////////////////////

function runCmd(callback, args = [], json = null, cmd = "/opt/fancontrol/fancontrol-cli.py") {
    var cbDone = function(data) {
        callback.call(this, data);
    };
    var cbFail = function(message, data) {
        callback.call(this, "[]");
        new msgBox(this, "FanControl command failed", "Command error: " + (data ? data : message + "<br>Please check the log file"));
    };
    var command = [cmd];
    command = command.concat(args);
    if (json) {
        command = command.concat(JSON.stringify(json));
    }
    return cockpit.spawn(command, { err: "out", superuser: "require" })
        .done(cbDone.bind(this))
        .fail(cbFail.bind(this));
}

function runLog(callback, args = [], cmd = "/opt/fancontrol/fancontrol-logger.py") {
    var cbDone = function(data) {
        callback.call(this, data, 0);
    };
    var cbFail = function(message, data) {
        callback.call(this, "[]", 1);
        //new msgBox(this, "FanControl command failed", "Command error: " + (data ? data : message));
    };
    var command = [cmd];
    command = command.concat(args);
    return cockpit.spawn(command, { err: "out", superuser: "require" })
        .done(cbDone.bind(this))
        .fail(cbFail.bind(this));
}

function buildOpts(data, refData = {}, exclude = []) {
    var opts = {};

    for (let key in data) {
        let addKey = true;
        if (exclude.includes(key)) {
            addKey = false;
        } else if (key in refData) {
            if (data2str(data[key]) == data2str(refData[key])) {
                addKey = false;
            }
        }
        if (addKey) {
            opts[key] = data[key];
        }
    }
    return opts;
}

function data2str(data) {
    var str = "";
    if (Array.isArray(data)) {
        str = data.map(s => s.trim()).join(",");
    } else {
        str = data.toString();
    }
    return str;
}

///////////////////////////
// Tab display functions //
///////////////////////////

function clickTab() {
    // remove active class from all elements
    document.querySelectorAll('[role="presentation"]').forEach(function (el) {
        el.classList.remove("active");
        el.getElementsByTagName("a")[0].setAttribute("tabindex", -1);
        el.getElementsByTagName("a")[0].setAttribute("aria-selected", false);
    });

    // add class 'active' to this element
    this.classList.add("active")
    this.getElementsByTagName("a")[0].setAttribute("aria-selected", true);
    this.getElementsByTagName("a")[0].removeAttribute("tabindex");

    // hide all contents
    document.querySelectorAll('[role="tabpanel"]').forEach(function (el) {
        el.setAttribute("aria-hidden", true);
        el.classList.remove("active");
        el.classList.remove("in");
    });

    // show current contents
    contentId = this.getElementsByTagName("a")[0].getAttribute("aria-controls");
    el = document.getElementById(contentId);

    el.setAttribute("aria-hidden", false);
    el.classList.add("active");
    el.classList.add("in");
    displayContent(el);
}

function displayContent(el) {
    if (el.id.search("monitor") >= 0) {
        let Monitor = new fcMonitor(el);
        Monitor.displayContent();
    } else if (el.id.search("fans") >= 0) {
        let Fan = new fcFans(el);
        Fan.displayContent();
    } else if (el.id.search("settings") >= 0) {
        let Fan = new fcSettings(el);
        Fan.displayContent();
    } else if (el.id.search("log") >= 0) {
        let Logger = new journalLogger(el, "fancontrol");
        Logger.displayContent();
    }
}

function displayFirstPane() {
    displayContent(document.querySelectorAll('[role="tabpanel"]')[0]);
}

document.querySelectorAll('[role="presentation"]').forEach(function (el) {
    el.addEventListener("click", clickTab);
});

displayFirstPane();

// Send a 'init' message.  This tells integration tests that we are ready to go
cockpit.transport.wait(function() { });
