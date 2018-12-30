/* The facial recognition module (detection + recognition) for MagicMirror².
 * This module is mainly inspired by the one developped by paviro/MMM-Facial-Recognition
 * and PeterVanco/MMM-Facial-Recognition-OCV3.
 * This module was build on top of Intel Movidius NCS stick. Related links and my
 * comments can be found https://ncsforum.movidius.com/discussion/comment/4111/
 * Copyright (C) 2019 Dmitry Studynskyi
 * License: GNU General Public License */

/* eslint-disable no-console */
// eslint-disable-next-line import/no-unresolved
const nodeHelper = require("node_helper");
const { PythonShell } = require("python-shell");

let pythonStarted = false;

module.exports = nodeHelper.create({

    start () {
        console.log(`Starting node helper for: ${this.name}`);
    },

    python_start () {
        const self = this;
        const pyShell = new PythonShell(`modules/${this.name}/python/FacialRecognition.py`, {
            pythonPath: "python3",
            mode: "json",
            args: [JSON.stringify(this.config)]
        });

        pyShell.on("message", (payload) => {
            if (payload.messageType) {
                switch (payload.messageType) {
                case "log":
                    console.log(`[${self.name}] ${payload.message}`);
                    break;
                case "login":
                    console.log(`[${self.name}] User ${payload.message.user} with confidence ${payload.message.distance} logged in.`);
                    self.sendSocketNotification("user", {
                        action: "FACIAL_RECOGNITION_LOGIN",
                        user: payload.message.user,
                        distance: payload.message.distance
                    });
                    break;
                case "logout":
                    console.log(`[${self.name}] User ${payload.message.user} logged out.`);
                    self.sendSocketNotification("user", {
                        action: "FACIAL_RECOGNITION_LOGOUT",
                        user: payload.message.user
                    });
                    break;
                case "matchResults":
                    if (this.config.debug) {
                        console.log(`[${self.name}] Number of matched users ${payload.message.matchedFaces.length}`);
                        self.sendSocketNotification("user", {
                            action: "FACIAL_MATCH_RESULTS",
                            matchedFaces: payload.message.matchedFaces
                        });
                    }
                    break;
                default:
                    console.log(`[${self.name}] Unsupported message was received with type "${payload.messageType}" and message "${payload.message}".`);
                }
            } else {
                console.log(`[${self.name}] Unrecognized message from python ${payload}`);
            }
        });

        pyShell.end((err) => {
            if (err) throw err;
            console.log(`[${self.name} finished running...`);
        });
    },

    // Subclass socketNotificationReceived received.
    socketNotificationReceived (notification, payload) {
        if (notification === "FACIAL_RECOGNITION_CONFIG") {
            this.config = payload;
            if (!pythonStarted) {
                pythonStarted = true;
                this.python_start();
            }
        }
    }

});
