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

## 📦 环境依赖

本项目包含 **Node.js** 和 **Python** 脚本，分别需要以下环境支持：

### Node.js 脚本

* Node.js ≥ 18.x
* 包管理器：推荐使用 [`pnpm`](https://pnpm.io/zh/installation)

安装依赖命令（需在项目根目录中）：

```bash
pnpm install
```

### Python 脚本

* Python ≥ 3.8
* 推荐使用 [`pip`](https://pip.pypa.io/en/stable/installation/) 安装依赖

安装依赖命令：

```bash
pip install -r requirements.txt
```

---

## 🗂️ 目录结构说明

```bash
ScriptsForQinglong/
├── README.md               # 项目说明文档
├── utils/                  # 公共工具函数或脚本依赖模块
├── node_scripts/           # Node.js 实现的业务逻辑
├── python_scripts/         # Python 脚本
├── config/                 # 一些配置模板或环境变量示例
└── requirements.txt        # Python 依赖文件（可选）
```

---

## 📮 联系与反馈

* 仓库作者：[@MoLing-Dong](https://github.com/MoLing-Dong)
* 如需反馈问题或建议，请提交 [Issue](https://github.com/MoLing-Dong/ScriptsForQinglong/issues)

---

## 📄 License

本项目采用 [MIT License](https://opensource.org/licenses/MIT) 开源许可协议。
