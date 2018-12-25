/* A MagicMirror module to show bus, luas and rail arrival times.
 * Copyright (C) 2018 Dmitry Studynskyi
 * License: GNU General Public License */

/* eslint-disable fp/no-mutating-methods,no-undef,guard-for-in,no-restricted-syntax */
// eslint-disable-next-line no-undef
Module.register("MMM-Facial-Recognition", {

    /* initialize */
    start () {
        this.current_user = null;
        this.sendSocketNotification("CONFIG", this.config);
        Log.log(`Starting module: ${this.name}`);
    }

});
