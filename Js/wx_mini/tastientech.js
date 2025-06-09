/**
 * #小程序://塔斯汀+/4mcUQx62ogk9QgE
 *
 * 抓包 Host：https://sss-web.tastientech.com 获取请求头 user-token 的值
 * export TASTI_TOKEN = 'sss7eXX-XXXXX-XXXX-XXXX-XXXX'
 * 多账号用 & 或换行
 *
 * @author Telegram@commonUtils
 * @site https://blog.imzjw.cn
 * @date 2024/12/17
 *
 * const $ = new Env('塔斯汀')
 * cron: 40 12 * * *
 */
const initScript = require('../utils/initScript')
const {$, notify, commonUtils, checkUpdate} = initScript('塔斯汀');
const tastList = process.env.TASTI_TOKEN ? process.env.TASTI_TOKEN.split(/[\n&]/) : [];
let message = '';
// 接口地址
const baseUrl = 'https://sss-web.tastientech.com'
// 签到活动ID
let signActivityId;
// 请求头
const headers = {
    'User-Agent': commonUtils.getRandomUserAgent(),
    'Content-Type': 'application/json',
    'version': '3.2.3',
    'channel': '1',
    'xweb_xhr': '1',
    'Referer': 'https://servicewechat.com/wx557473f23153a429/378/page-frame.html',
    'Accept-Language': 'zh-CN,zh;q=0.9'
};

!(async () => {
    await checkUpdate($.name, tastList);
    console.log(`\n已随机分配 User-Agent\n\n${headers['user-agent'] || headers['User-Agent']}`);
    for (let i = 0; i < tastList.length; i++) {
        const index = i + 1;
        console.log(`\n*****第[${index}]个${$.name}账号*****`);
        headers['user-token'] = tastList[i];
        message += `📣====${$.name}账号[${index}]====📣\n`;
        await main();
        await $.wait(commonUtils.getRandomWait(2000, 2500));
    }
    if (message) {
        await notify.sendNotify(`「${$.name}」`, `${message}`);
    }
})().catch((e) => $.logErr(e)).finally(() => $.done());

async function main() {
    await getActivityId()
    await $.wait(commonUtils.getRandomWait(1e3, 2e3));
    await getUserInfo();
    await $.wait(commonUtils.getRandomWait(1e3, 2e3));
    await getPoint();
}

/**
 * 自动获取签到 ID
 *
 * @returns {Promise<void>}
 */
async function getActivityId() {
    try {
        let data = await commonUtils.sendRequest(`${baseUrl}/api/minic/shop/intelligence/banner/c/list`, 'post', headers);
        if (200 !== data.code) {
            return console.error(`获取活动ID失败 ->`, data.msg);
        }
        const dailySignInBanner = data.result.find(item => item.bannerName === '每日签到');
        if (!dailySignInBanner) {
            return console.error('未找到每日签到活动');
        }
        // 解析 jumpPara 字段
        const jumpPara = JSON.parse(dailySignInBanner.jumpPara);
        if (!jumpPara || !jumpPara.path) {
            return console.error('jumpPara 结构不符合预期:', jumpPara);
        }
        const decodedPath = decodeURIComponent(jumpPara.path);
        const urlParams = new URLSearchParams(new URL(decodedPath, 'https://example.com').search);
        const jumpCode = urlParams.get('jumpCode');
        const encodedJumpPara = urlParams.get('jumpPara');
        if (!jumpCode || !encodedJumpPara) {
            return console.error('查询参数不符合预期:', decodedPath);
        }
        // 解码 jumpPara
        const decodedJumpPara = decodeURIComponent(encodedJumpPara);
        // 解析 jumpPara JSON
        const jumpParaObj = JSON.parse(decodedJumpPara);
        if (!jumpParaObj || !jumpParaObj.activityId) {
            return console.error('jumpPara JSON 结构不符合预期:', decodedJumpPara);
        }
        signActivityId = jumpParaObj.activityId;
        const today = new Date();
        const month = today.getMonth() + 1;
        const day = today.getDate();
        console.log(`${month}月${day}日-签到活动ID: ${signActivityId}`);
    } catch (e) {
        console.error(`获取活动ID时发生异常：${e}`);
    }
}

async function getUserInfo() {
    try {
        let data = await commonUtils.sendRequest(`${baseUrl}/api/intelligence/member/getMemberDetail`, 'get', headers);
        if (200 !== data.code) {
            return console.log(`获取用户信息失败 ->`, data.msg);
        }
        const {nickName, phone} = data.result;
        const hiddenMobile = `${phone.slice(0, 3)}***${phone.slice(-3)}` || '18888888888';
        console.log(`${nickName}(${hiddenMobile})`);
        message += `${nickName}(${phone})\n`;
        await $.wait(commonUtils.getRandomWait(1e3, 2e3));
        data = await commonUtils.sendRequest(`${baseUrl}/api/sign/member/signV2`, 'post', headers, {
            "activityId": signActivityId,
            "memberName": nickName,
            "memberPhone": phone
        });
        if (200 !== data.code) {
            message += `签到失败：${data.msg}\n`;
            return console.log(`签到失败 ->`, data.msg);
        }
        if (!data.result.rewardInfoList[0].rewardName) {
            console.log(`签到成功，积分+${data.result.rewardInfoList[0].point}`);
            message += `签到成功，积分+${data.result.rewardInfoList[0].point}\n`;
        } else {
            console.log(`签到成功，获得奖品；${data.result.rewardInfoList[0].rewardName}`);
            message += `签到成功，获得奖品；${data.result.rewardInfoList[0].rewardName}\n`;
        }
    } catch (e) {
        console.error(`获取用户信息或签到时发生异常：${e}`);
    }
}

/**
 * 获取积分
 *
 * @returns {Promise<void>}
 */
async function getPoint() {
    try {
        let data = await commonUtils.sendRequest(`${baseUrl}/api/wx/point/myPoint`, 'post', headers);
        if (200 !== data.code) {
            return console.log(`获取积分失败 ->`, data.msg);
        }
        console.log(`当前积分：${data.result.point}`);
        message += `当前积分：${data.result.point}\n\n`;
    } catch (e) {
        console.error(`获取积分时发生异常：${e}`);
    }
}
