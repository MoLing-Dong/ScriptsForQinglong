module.exports = function getEnv(envName) {
  /**
   * @Created by Mol on 2024/02/27
   * @description 获取环境变量
   * @param {String} envName 环境变量名称
   */
  envName = envName.toUpperCase().trim();

  let environmentVariable = [
    "", //第一个
    "", //第二个
  ];
  let IP = "";
  // 判断环境变量里面是否有environmentVariable
  if (process.env.envName) {
    console.log(`\n环境变量：${process.env.envName}\n`);
    if (process.env.envName.indexOf("&") > -1) {
      environmentVariable = process.env.envName.split("&");
    } else if (process.env.envName.indexOf("\n") > -1) {
      environmentVariable = process.env.envName.split("\n");
    } else {
      environmentVariable = [process.env.envName];
    }
  } else {
    console.log(`\n环境变量：${process.env}\n`);
  }
  if (JSON.stringify(process.env).indexOf("GITHUB") > -1) {
    console.log(
      `请勿使用github action运行此脚本,无论你是从你自己的私库还是其他哪里拉取的源代码，都会导致我被封号\n`
    );
  }
  //!(async () => {
  //	IP = await getIP();
  //    try {
  //        IP = IP.match(/((2(5[0-5]|[0-4]\d))|[0-1]?\d{1,2})(\.((2(5[0-5]|[0-4]\d))|[0-1]?\d{1,2})){3}/)[0];
  //        console.log(`\n当前公网IP: ${IP}`);
  //    } catch (e) { }
  //})()
  environmentVariable = [
    ...new Set(environmentVariable.filter((item) => !!item)),
  ];
  if (process.env.DEBUG && process.env.DEBUG === "false")
    console.log = () => {};
  console.log(
    `\n====================共${environmentVariable.length}个任务=================\n`
  );
  console.log(
    `============脚本执行时间：${formatdate(
      new Date(
        new Date().getTime() +
          new Date().getTimezoneOffset() * 60 * 1000 +
          8 * 60 * 60 * 1000
      )
    )}=============\n`
  );

  for (let i = 0; i < environmentVariable.length; i++) {
    environmentVariable[i] = environmentVariable[i].replace(
      /[\u4e00-\u9fa5]/g,
      (str) => encodeURI(str)
    );
  }
  // let permit = process.env.PERMIT_JS ? process.env.PERMIT_JS.split("&") : "";

  // if (process.env.DP_POOL) {
  //   if (
  //     permit &&
  //     permit.filter((x) => process.mainModule.filename.includes(x)).length != 0
  //   ) {
  //     try {
  //       require("global-agent/bootstrap");
  //       global.GLOBAL_AGENT.HTTP_PROXY = process.env.DP_POOL;
  //       console.log(`\n---------------使用代理池模式---------------\n`);
  //     } catch {
  //       throw new Error(`请安装global-agent依赖，才能启用代理！`);
  //     }
  //   } else {
  //   }
  // }
  function getIP() {
    const https = require("https");
    return new Promise((resolve, reject) => {
      let opt = {
        hostname: "www.cip.cc",
        port: 443,
        path: "/",
        method: "GET",
        headers: {
          "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36",
        },
        timeout: 5000,
      };
      const req = https.request(opt, (res) => {
        res.setEncoding("utf-8");
        let tmp = "";
        res.on("error", reject);
        res.on("data", (d) => (tmp += d));
        res.on("end", () => resolve(tmp));
      });

      req.on("error", reject);
      req.end();
    });
  }

  // 获取当前活动脚本的文件名
  function GetCurrentActivityScriptFileName() {
    const path = require("path");
    return path.basename(process.argv[1]);
  }

  function formatdate(date) {
    const year = date.getFullYear();
    const month = ("0" + (date.getMonth() + 1)).slice(-2);
    const day = ("0" + date.getDate()).slice(-2);
    const hours = ("0" + date.getHours()).slice(-2);
    const minutes = ("0" + date.getMinutes()).slice(-2);
    const seconds = ("0" + date.getSeconds()).slice(-2);
    return `${year}/${month}/${day} ${hours}:${minutes}:${seconds}`;
  }

  return environmentVariable;
};
