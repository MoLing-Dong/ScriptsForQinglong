module.exports = (appName) => {
    const Env = require('./env');
    const $ = new Env(appName);
    const notify = $.isNode() ? require('./sendNotify') : '';
    const commonUtils = require('./common');
    const checkUpdate = require('./envCheck');
    return {
        $,
        notify,
        commonUtils,
        checkUpdate
    };
};