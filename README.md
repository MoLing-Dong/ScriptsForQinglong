# ScriptsForQinglong

## 📘 简介

本仓库用于存放个人自用的青龙面板自动化脚本，涵盖日常任务、账号工具、监控辅助等用途。
所有脚本适用于 **青龙面板（QingLong）** 的定时任务环境，便于自动执行。

> ⚠️ 脚本仅供学习交流使用，**严禁用于任何商业用途或非法用途**。如有侵权请联系删除。

---

## 🚀 快速开始

### 1. 拉取仓库脚本至青龙

在青龙面板中任务管理页面，使用如下命令添加定时任务拉取脚本：

```shell
ql repo https://github.com/MoLing-Dong/ScriptsForQinglong.git "" "utils" "utils" "main"
```

> 参数说明：
>
> * 第1个空字符串：表示拉取所有脚本
> * 第2个 `"utils"`：排除 utils 目录中的文件（一般为依赖工具）
> * 第3个 `"utils"`：白名单，仅保留 utils 目录中的内容（具体根据项目结构决定）
> * `"main"`：分支名，默认主分支为 `main`

---

## 配置文件修改

```shell
## ql repo命令拉取脚本时需要拉取的文件后缀，直接写文件后缀名即可
RepoFileExtensions="js mjs py pyc sh"

## 取消推送一言
export HITOKOTO=false
```

## 🗂️ 目录结构说明

```bash
ScriptsForQinglong/
├── README.md               # 项目说明文档
├── LICENSE                 # 开源许可协议
├── SECURITY.md             # 安全策略文档
├── package.json            # Node.js 项目配置
├── pnpm-lock.yaml          # pnpm 锁定文件
├── Js/                     # 存放 JavaScript 脚本
│   ├── utils/              # 存放 JavaScript 工具脚本
│   │   ├── common.js       # 通用工具函数
│   │   ├── env.js          # 环境变量处理
│   │   ├── envCheck.js     # 环境检查工具
│   │   └── initScript.js   # 初始化脚本
│   ├── other/              # 其他 JS 脚本
│   │   └── authCheck.js    # 认证检查脚本
│   └── wx_mini/            # 微信小程序相关脚本
│       └── tastientech.js  # 微信小程序脚本
├── Py/                     # 存放 Python 脚本
│   ├── utils/              # 存放 Python 工具脚本
│   │   ├── __init__.py     # Python 包初始化文件
│   │   ├── pyEnv.py        # Python 环境工具
│   │   └── js_reverse/     # JavaScript 反编译工具
│   │       └── wyy_reverse.js  # 网易云音乐反编译脚本
│   ├── aiMorningBrief.py   # AI 晨报脚本
│   ├── by.py               # 其他功能脚本
│   ├── demo.py             # 演示脚本
│   ├── electricityBill.py  # 电费查询脚本
│   ├── hackerNews.py       # 黑客新闻脚本
│   ├── test.py             # 测试脚本
│   ├── wyyYyr.py           # 网易云音乐相关脚本
│   └── xiaomiWallet.py     # 小米钱包脚本
└── Sh/                     # 存放 Shell 脚本
    └── dependency-check.sh # 依赖检查脚本
```

---

## 📮 联系与反馈

* 仓库作者：[@MoLing-Dong](https://github.com/MoLing-Dong)
* 如需反馈问题或建议，请提交 [Issue](https://github.com/MoLing-Dong/ScriptsForQinglong/issues)

---

## 📄 License

本项目采用 [MIT License](https://opensource.org/licenses/MIT) 开源许可协议。
