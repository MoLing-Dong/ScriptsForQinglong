/**
 * 检测现有脚本仓库（https://github.com/commonUtils/AutoTaskScript）凭证（Token、Cookie）等是否失效
 * 目前只推送失效的账号，每天跑两次即可，没有推送消息就说明没有账号失效
 * 默认关闭，如需启用设置变量为 true
 * export ENABLE_CHECK_TOKEN = 'true'
 *
 * @author 
 * @site 
 * @date 
 *
 * const $ = new Env('多合一账号失效检测')
 * cron: 10 12,21 * * *
 */
const initScript = require('../utils/initScript')
const {
    $,
    notify,
    commonUtils
} = initScript('多合一账号失效检测');
const cheerio = require("cheerio");
const crypto = require("crypto");
// 消息推送
let message = '';
// 环境变量
const enableCheckToken = process.env.ENABLE_CHECK_TOKEN || false;
// 账号列表
const accounts = [
    // {
    //     name: '甄稀冰淇淋',
    //     list: process.env.ZX_ICE_TOKEN ? process.env.ZX_ICE_TOKEN.split(/[\n&]/) : [],
    //     checkFn: async (token) => {
    //         const data = await commonUtils.sendRequest('https://msmarket.msx.digitalyili.com/gateway/api/auth/account/user/info', 'get', createHeaders('wx_mini', `access-token@${token}`, 'Content-Type@application/json', 'referer@https://servicewechat.com/wx21fd8b5d6d4cf1ca/195/page-frame.html'));
    //         return !data.status || !data.data.userId;
    //     },
    // },
    
];

!(async () => {
    if (!enableCheckToken) {
        console.log('\n如需执行，请先配置环境变量【ENABLE_CHECK_TOKEN】为 true');
        return;
    }
    for (const account of accounts) {
        if (!account.list.length) {
            console.log(`\n未配置${account.name}环境变量，跳过...`);
            await $.wait(commonUtils.getRandomWait(500, 1000));
            continue;
        }
        let totalAccounts = account.list.length;
        let failedAccounts = 0;
        let failedIndices = [];
        for (let i = 0; i < totalAccounts; i++) {
            if (account.name === '贴吧任务签到') {
                if (!account.list[i].includes('CUID=')) {
                    console.log('\n检测到贴吧任务签到变量缺少 CUID，将跳过...');
                    continue;
                }
            }
            const index = i + 1;
            console.log(`\n${account.name}账号[${index}]`);
            const isLoginFailed = await checkAccount(account, account.list[i]);
            await $.wait(commonUtils.getRandomWait(800, 1100));
            if (isLoginFailed) {
                console.error(`失效！❌`);
                failedAccounts++;
                failedIndices.push(index);
            } else {
                console.log(`有效！✅`);
            }
        }
        if (failedAccounts > 0) {
            message += `${account.name}\n`;
            message += `共计[${totalAccounts}]个账号\n`;
            message += `第[${failedIndices.join(', ')}]个账号失效\n\n`;
            message += `------------\n\n`;
        }
    }
    if (message) {
        await notify.sendNotify(`「${$.name}」`, `${message}`);
    } else {
        console.log('\n检测完毕，暂无失效账号！✅');
    }
})().catch((e) => $.logErr(e)).finally(() => $.done());

async function checkAccount(account, token) {
    try {
        return await account.checkFn(token);
    } catch (e) {
        return true;
    }
}

/**
 * 创建请求头
 *
 * @param type
 * @param customHeaders
 */
function createHeaders(type, ...customHeaders) {
    const headers = {
        'User-Agent': commonUtils.getRandomUserAgent(type),
    };
    customHeaders.forEach(customHeader => {
        const [key, value] = customHeader.split('@');
        if (key && value) {
            headers[key] = value;
        }
    });
    return headers;
}

/**
 * 老板电器 token 获取
 *
 * @param openId
 * @returns {{openid, is_need_sync: number, timestamp: number, token: string}}
 */
function getLaoBanToken(openId) {
    const currentTimestampMs = Date.now();
    const rawString = `${currentTimestampMs}wqewq${openId}`;
    return {
        is_need_sync: 1,
        timestamp: currentTimestampMs,
        token: commonUtils.md5(rawString),
        openid: openId
    }
}