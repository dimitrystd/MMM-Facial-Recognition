/* The facial recognition module (detection + recognition) for MagicMirror².
 * This module is mainly inspired by the one developped by paviro/MMM-Facial-Recognition
 * and PeterVanco/MMM-Facial-Recognition-OCV3.
 * This module was build on top of Intel Movidius NCS stick. Related links and my
 * comments can be found https://ncsforum.movidius.com/discussion/comment/4111/
 * Copyright (C) 2019 Dmitry Studynskyi
 * License: GNU General Public License */

/* eslint-disable fp/no-mutating-methods,no-undef,guard-for-in,no-restricted-syntax */
// eslint-disable-next-line no-undef
Module.register("MMM-Facial-Recognition", {

    defaults: {
        // Threshold for the distance of a recognized face before it's considered a
        // positive match.  Confidence values below this threshold will be considered
        // a positive match because the lower the distance value, or distance, the
        // more confident the algorithm is that the face was correctly detected.
        threshold: 0.3,
        // Force the use of a usb webcam on raspberry pi
        // (on other platforms this is always true automatically)
        // This parameter is not used right now, code always uses usb webcam
        useUSBCam: true,
        // Recognition interval in milliseconds (smaller number = faster but CPU intens!)
        interval: 1000,
        // Logout delay after last recognition so that a user does not get instantly logged out
        // if he turns away from the mirror for a few seconds
        logoutDelay: 15,
        // Module set used for strangers and if no user is detected
        defaultClass: "default",
        // Set of modules which should be shown for every user
        everyoneClass: "everyone",
        // Boolean to toggle welcomeMessage
        welcomeMessage: true,
        // Send CURRENT_USER event to other modules
        broadcastEvents: false,
        // Show debug information
        debug: true
    },

    /* initialize */
    start() {
        this.current_user = null;
        this.loginTimeout = null;
        this.matchedFaces = [];
        this.loaded = false;
        this.sendSocketNotification("FACIAL_RECOGNITION_CONFIG", this.config);
        Log.info(`Starting module: ${this.name}`);
    },

    /* build the HTML to render */
    getDom () {
        const wrapper = document.createElement("table");
        wrapper.className = "small";

        if (this.matchedFaces.length === 0) {
            wrapper.innerHTML = (this.loaded) ? this.translate("noFaces") : this.translate("loading");
            wrapper.className = "small dimmed";
            return wrapper;
        }

        for (const mf in this.matchedFaces) {
            const matchedFace = this.matchedFaces[mf];
            const rowWrapper = document.createElement("tr");
            rowWrapper.className = "normal";

            const userWrapper = document.createElement("td");
            userWrapper.className = "userlogin";
            userWrapper.innerText = matchedFace.user_login;
            rowWrapper.appendChild(userWrapper);

            const distaneWrapper = document.createElement("td");
            distaneWrapper.className = "distance";
            distaneWrapper.innerText = matchedFace.distance;
            rowWrapper.appendChild(distaneWrapper);

            wrapper.appendChild(rowWrapper);
        }

        return wrapper;
    },

    login_user() {
        if (this.loginTimeout != null) {
            clearTimeout(this.loginTimeout);
        }
        const self = this;
        MM.getModules()
            .withClass(this.config.defaultClass)
            .exceptWithClass(this.config.everyoneClass)
            .enumerate((module) => {
                module.hide(1000, () => {
                    Log.log(`${module.name} is hidden by ${self.name}.`);
                },
                { lockString: self.identifier });
            });

        MM.getModules()
            .withClass(this.current_user)
            .enumerate((module) => {
                module.show(1000, () => {
                    Log.log(`${module.name} is shown by ${self.name}.`);
                },
                { lockString: self.identifier });
            });

        if (this.config.broadcastEvents) {
            this.sendNotification("CURRENT_USER", this.current_user);
        }
    },

    logout_user() {
        const self = this;

        MM.getModules()
            .withClass(this.current_user)
            .enumerate((module) => {
                module.hide(1000, () => {
                    Log.log(`${module.name} is hidden by ${self.name}.`);
                },
                { lockString: self.identifier });
            });

        MM.getModules()
            .withClass(this.config.defaultClass)
            .exceptWithClass(this.config.everyoneClass)
            .enumerate((module) => {
                module.show(1000, () => {
                    Log.log(`${module.name} is shown by ${self.name}.`);
                },
                { lockString: self.identifier });
            });

        if (this.config.broadcastEvents) {
            this.sendNotification("CURRENT_USER", "None");
        }
    },

    UNKNOWN_USER: "Stranger",

    // Override socket notification handler.
    socketNotificationReceived (notification, payload) {
        if (payload.action === "FACIAL_RECOGNITION_LOGIN") {
            if (payload.user === this.UNKNOWN_USER) {
                // this.current_user = this.translate("stranger");
                this.current_user_id = payload.user;
                const self = this;
                this.loginTimeout = setTimeout(() => {
                    self.logout_user();
                    self.current_user = null;
                }, this.config.logoutDelay);
                return;
            }

            if (this.current_user_id !== payload.user) {
                this.logout_user();
            }

            this.current_user = payload.user; //this.config.users[payload.user];
            this.current_user_id = payload.user;
            this.login_user();

            if (this.config.welcomeMessage) {
                this.sendNotification("SHOW_ALERT", {
                    type: "notification",
                    title: "Login",
                    message: this.translate("message").replace("%person", this.current_user),
                    timer: 5000
                });
            }
        } else if (payload.action === "FACIAL_RECOGNITION_LOGOUT") {
            this.sendNotification("SHOW_ALERT", {
                type: "notification",
                title: "Logout",
                message: payload.user,
                timer: 5000
            });
            if (payload.user === this.UNKNOWN_USER) {
                // ignore stranger
                return;
            }

            if (this.loginTimeout != null) {
                clearTimeout(this.loginTimeout);
            }

            const self = this;
            this.loginTimeout = setTimeout(() => {
                self.logout_user();
                self.current_user = null;
            }, this.config.logoutDelay);
        } else if (payload.action === "FACIAL_MATCH_RESULTS") {
            this.matchedFaces = payload.matchedFaces;
            this.loaded = true;
            this.updateDom();
        }
    },

    // eslint-disable-next-line no-unused-vars
    notificationReceived(notification, payload, sender) {
        if (notification === "DOM_OBJECTS_CREATED") {
            const self = this;
            MM.getModules()
                .exceptWithClass("default")
                .enumerate((module) => {
                    module.hide(1000, () => {
                        Log.log("Module is hidden.");
                    }, { lockString: self.identifier });
                });
        }
    },

    // Define required translations.
    getTranslations() {
        return {
            en: "translations/en.json"
        };
    }
});
