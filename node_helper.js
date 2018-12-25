/* eslint-disable no-console */
/* A MagicMirror module to show bus, luas and rail arrival times.
 * Copyright (C) 2018 Dmitry Studynskyi
 * License: GNU General Public License */

// eslint-disable-next-line import/no-unresolved
const nodeHelper = require("node_helper");
const {PythonShell} = require("python-shell");

let pythonStarted = false;

module.exports = nodeHelper.create({

    start () {
        console.log(`Starting node helper for: ${this.name}`);
    },

    python_start () {
        const self = this;
        const pyshell = new PythonShell(`modules/${this.name}/python/FacialRecognition.py`, {
            pythonPath: "python3",
            mode: "json",
            args: [JSON.stringify(this.config)]
        });

        pyshell.on("message", (message) => {
            if (message.hasOwnProperty("log")) {
                console.log(`[${self.name}] ${message.log}`);
            }
            if (message.hasOwnProperty("status")) {
                console.log(`[${self.name}] ${message.status}`);
            }
            if (message.hasOwnProperty("login")) {
                console.log(`[${self.name}] ` + `User ${self.config.users[message.login.user - 1]} with confidence ${message.login.confidence} logged in.`);
                self.sendSocketNotification("user", {
                    action: "login",
                    user: message.login.user - 1,
                    confidence: message.login.confidence
                });
            }
            if (message.hasOwnProperty("logout")) {
                console.log(`[${self.name}] ` + `User ${self.config.users[message.logout.user - 1]} logged out.`);
                self.sendSocketNotification("user", { action: "logout", user: message.logout.user - 1 });
            }
            if (message.hasOwnProperty("motion-detected")) {
                console.log("motion detected");
                self.sendSocketNotification("MOTION_DETECTED", {});
                // self.activateMonitor();
            }
            if (message.hasOwnProperty("motion-stopped")) {
                console.log("motion stopped");
                self.sendSocketNotification("MOTION_STOPPED", {});
                // self.deactivateMonitor();
            }
        });

        pyshell.end((err) => {
            if (err) throw err;
            console.log(`[${self.name} finished running...`);
        });
    },

    // Subclass socketNotificationReceived received.
    socketNotificationReceived (notification, payload) {
        if (notification === "CONFIG") {
            this.config = payload;
            if (!pythonStarted) {
                pythonStarted = true;
                this.python_start();
            }
        }
    }

});
