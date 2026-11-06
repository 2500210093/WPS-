# 每日签到 · WPS + 网易云音乐

标准 Python 项目结构。每天自动签到，结果通过飞书自定义机器人推送。

- **WPS**：每日签到 + 每日任务
- **网易云音乐**：仅每日签到（无刷歌、无等级查询），使用标准 weapi 加密
- **通知**：飞书群机器人卡片消息，支持签名校验
- **运行**：GitHub Actions 定时执行，也可在服务器本地运行

---

## 目录结构（请严格保持，不要改路径）

```
.github/workflows/daily.yml   GitHub Actions 定时任务（必须在这一层）
sign/__init__.py              包标记
sign/wps.py                   WPS 签到
sign/netease.py               网易云每日签到（weapi 加密）
run.py                        入口：依次执行两个平台 + 汇总 + 推送
notify.py                     飞书机器人推送
config.json.example           本地配置模板
requirements.txt              Python 依赖
README.md                     本文件
上传说明.md                    往 GitHub 传文件的逐步教程
只差一个文件.md                拖拽漏掉 .github 后的补救步骤（本地看，不用传）
粘贴用-daily.yml.txt           workflow 纯文本，供复制粘贴（本地用，不用传）
.gitignore                    忽略 config.json / 日志 / 缓存
```

> `.github/workflows/daily.yml` 是最容易放错的文件。放在仓库根目录的 `daily.yml` **不会被 GitHub Actions 识别**。
>
> ⚠️ GitHub 网页的**拖拽上传会忽略点开头的目录**（`.github/`、`.gitignore`）。如果拖完发现上传框里只有散装文件、没有 `.github/workflows/daily.yml`，别重传：用 **Add file → Create new file**，文件名填 `.github/workflows/daily.yml`，内容从 `粘贴用-daily.yml.txt` 全选复制。详见 `只差一个文件.md`。

---

## 一、GitHub Actions 部署

### 1. 上传文件

按 `上传说明.md` 操作，确认仓库里能看到 `.github` 文件夹，且路径为 `.github/workflows/daily.yml`。

### 2. 创建飞书机器人

飞书群 → 群设置 → 群机器人 → 添加自定义机器人 → 复制 Webhook。

安全设置二选一：

| 选择 | 需要填的 Secret |
|------|-----------------|
| 自定义关键词，填 `签到` | `FEISHU_WEBHOOK` |
| 签名校验 | `FEISHU_WEBHOOK` + `FEISHU_SECRET`（签名密钥） |

### 3. 添加仓库 Secrets

Settings → Secrets and variables → Actions → New repository secret

| Name | 内容 | 必需 |
|------|------|------|
| `WPS_COOKIE` | WPS Cookie | 是 |
| `NETEASE_COOKIE` | 网易云音乐 Cookie（含 `__csrf`） | 是 |
| `FEISHU_WEBHOOK` | 机器人完整 Webhook | 是 |
| `FEISHU_SECRET` | 签名密钥 | 仅开启签名校验时 |

值直接粘贴原文，不加引号、不留空格或换行。

### 4. 运行

- 手动：Actions → 「每日签到（WPS + 网易云音乐）」→ Run workflow。
- 自动：**每天北京时间 20:00**（`cron: '0 12 * * *'`，GitHub Actions 按 UTC 解析）。

---

## 二、每天自动跑的说明

`daily.yml` 开头：

```yaml
on:
  workflow_dispatch:
  schedule:
    - cron: '0 12 * * *'
```

- GitHub Actions 的 cron 使用 **UTC**，`0 12 * * *` = 12:00 UTC = 北京时间 20:00。
- 想改时间：cron 小时 = 北京时间 − 8（不够减则 +24）。例如北京 08:00 → `0 0 * * *`。
- 提交到默认分支后定时即生效，**不会立刻跑一次**，要等下一个时间点；想马上验证用 Run workflow。
- 定时触发的运行，摘要里显示「定时 / Scheduled」而不是「手动触发」。
- 仓库连续 **60 天无活动**，GitHub 会自动停用定时任务，需到 Actions 页面重新启用；偶尔手动 Run 一次即可保持活跃。
- 私有仓库免费额度每月 2000 分钟，每天一次（约 20 秒）完全够用。
- 任一平台失败时 `run.py` 返回退出码 1，该次运行会标红，飞书仍会收到含失败原因的卡片。

---

## 三、本地 / 服务器运行

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp config.json.example config.json
# 编辑 config.json 填入 Cookie 与 Webhook
python run.py
```

定时（crontab，每天 20:00）：

```bash
0 20 * * * cd /path/to/project && ./venv/bin/python run.py >> sign.log 2>&1
```

配置优先级：**环境变量 > config.json**。GitHub Actions 用 Secrets 注入环境变量，不需要 `config.json`。

---

## 四、Cookie 获取

- **WPS**：登录 <https://vip.wps.cn> → `F12` → Network → 刷新 → 复制完整 Cookie。
- **网易云音乐**：登录 <https://music.163.com> → `F12` → Network → 复制完整 Cookie，**必须包含 `__csrf`**，weapi 请求需要 `csrf_token`。

Cookie 有有效期，失效后飞书通知里会带出具体错误码，重新获取并更新 Secret 即可。

---

## 五、常见问题

| 现象 | 原因 | 处理 |
|------|------|------|
| Actions 里看不到这个 workflow | `daily.yml` 不在 `.github/workflows/` 下 | 核对目录结构 |
| `Could not open requirements file` | 用了旧 workflow 或漏传文件 | 用本包覆盖 `daily.yml`（新版直接安装依赖，不读 requirements.txt） |
| `::error::run.py 仍是旧版` | 只传了 workflow，Python 文件没覆盖 | 全覆盖 4 个 `.py` 文件 |
| `未配置 WPS_COOKIE` | Secret 名拼错或没填 | 核对 Secrets |
| 签到成功但飞书没消息 | Webhook 没填 / 开了签名校验没填密钥 | 核对机器人安全设置 |
| `code=400` / `code=301` 之外的错误 | Cookie 失效或网易云接口策略变更 | 重新获取 Cookie；错误码会显示在通知里 |
| `今日已签到（无需重复）` | 当天已签过 | 正常，按成功计 |

---

## 六、安全

- Cookie 与 Webhook 只放 Secrets 或本地 `config.json`，不要提交到仓库。
- `config.json`、`*.log` 已在 `.gitignore` 中。
- 建议定期更新 Cookie。

---

## 七、实现说明

网易云 `/weapi/point/dailySignin` 要求 weapi 加密：`params` 为双层 AES-CBC → Base64，`encSecKey` 为 RSA 加密的随机密钥，因此依赖 `pycryptodome`。若该路径失败，会降级尝试旧版明文接口 `/api/point/dailySignin`；两条路径都只执行「每日签到」这一个动作。

本项目交付前做过离线验证（语法、加密参数、签名、流程模拟），**未使用真实 Cookie 请求线上接口**，首次上线请手动触发一次 workflow。
