# 研报阅读室

已搭建一个纯静态研报网站，首页以手机用户为主，使用简洁单列研报目录：主题标题为重点，辅以机构、分类、日期、简介和标签，整行点击进入解读。按原报告日期从新到旧排列。现有瑞银研报已接入。首页通过 JavaScript 读取独立的 `reports.json` 并展示列表；无需登录、数据库、运行中的后端或前端依赖安装。

## 目录与上传边界

```text
研报分析/
├── originals/                     私有：官方研报原稿，不上传
│   └── 2026/10/原稿.pdf
├── prompts/                       私有：你常用的生成提示词，不上传
├── reports/                       编辑区：生成的研报和目录信息，不直接上传
│   └── 2026/ubs-us-semiconductor-20261019/
│       ├── index.html             面向用户的研报解读
│       ├── meta.json              标题、机构、日期、摘要、标签及发布开关
│       └── assets/                可选：该篇专用的图片、样式、脚本
├── site/                          列表页模板和公共素材
├── scripts/                       本地构建与新建草稿工具
├── dist/                          自动生成：唯一需要上传的目录
│   ├── index.html                 固定首页，新增报告无需改动
│   ├── reports.json               公开目录数据，新增报告后更新
│   ├── assets/
│   └── reports/2026/…/index.html
└── release.zip                    自动生成：dist 内容压缩包，方便上传
```

`originals/` 默认被 Git 忽略，请自行备份。`dist/` 可随时重新生成，不要直接编辑。构建程序仅选取 `published: true` 的研报，且不会将 `meta.json` 中的原稿路径输出到网站。报告正文是公开内容，发布前请自行核对。

## 日常操作

1. 把官方原稿放进 `originals/年份/月份/`。
2. 新建草稿（也可以直接复制现有报告目录，再改标题、日期等）：

   ```sh
   python3 scripts/new_report.py report-topic-20261021 --date 2026-10-21 --title "报告标题" --institution "机构名称"
   ```

3. 提供原稿和你的提示词，让助手把 HTML 写入该目录的 `index.html`。专用素材使用同目录 `assets/` 相对路径。
4. 检查内容，补齐 `meta.json` 的摘要、分类、地区、标签，并把 `published` 改为 `true`。列表摘要是人工/助手填写的元数据，构建程序不会从 PDF 自动提取或审核观点。
5. 生成网站和上传包：

   ```sh
   python3 scripts/build.py --zip
   ```

6. 首次部署：将 **dist 里面的所有内容** 上传至服务器网站根目录；或上传 `release.zip` 并在根目录解压。后续增量更新：只上传 `dist/reports/年份/新报告目录/` 和 `dist/reports.json`，先报告、后 JSON。不需要重新上传首页。只有修改首页设计或脚本时才更新 `index.html` 和 `assets/`。不要上传整个项目。服务器只需提供静态文件。

如果部署在 `https://example.com/research/`，将 dist 内容放进对应的 research 目录即可，网站内部使用相对路径。

## 预览与更新

```sh
python3 -m http.server 8000 --bind 127.0.0.1 --directory dist
```

打开 http://127.0.0.1:8000/ 。首页需要通过 HTTP(S) 加载 JSON，不支持双击本地 HTML 文件预览列表。

每次新增/修改后在本地重新构建；服务器可以只增量上传新报告目录及完整的 `reports.json`。JSON 是当前全部已发布报告的目录，不是仅包含新报告的补丁。将 `published` 设为 `false` 可从新构建的入口与输出移除该报告。**已经上传的旧 HTML 不会因此自动从服务器删除**，撤稿时需要删除服务器对应目录；列表取消入口不等于阻止访问。

保留已经发布的英文目录名，可保持分享链接稳定。手动上传时先上传新报告和素材，最后上传 `reports.json`；有条件时先解压至临时目录再整体切换。`reports.json` 建议配置 `Cache-Control: no-cache`（若使用 CDN，也需要遵循该缓存设置）；首页与研报 HTML 使用短缓存，避免用户看到旧内容。

## 为什么先用纯静态

当前流程是“收集原稿 → 按提示词生成 HTML → 手动上传 → 用户浏览”。首页读取静态 JSON 展示主题列表，研报元数据在本地 `meta.json` 中管理，Python 仅在本地构建时使用，服务器不需要 Python。

这让部署、备份和迁移都只涉及普通文件，页面也能在没有外部字体/CDN的情况下加载。当前默认所有部署出去的内容均可被直接访问。

以后出现以下需求，再引入相应能力：

| 新需求 | 可增加的能力 |
| --- | --- |
| 自动上传 | CI/部署脚本，继续保持纯静态，不必加数据库 |
| 在线新增、编辑、审核 | 管理后台 + 服务端 API + 数据库 |
| 会员、付费、不同用户权限 | 身份认证 + 服务端授权；不能只靠前端隐藏链接 |
| 多人同步维护、全文检索大量报告 | 内容管理/检索服务，必要时数据库 |
| 收藏、阅读历史跨设备同步 | 用户系统 + 数据库 |

当前构建工具只有 Python 标准库依赖。后续自动化可以复用 `python3 scripts/build.py --zip`，无须重写网站。

## 从旧版首页切换

首次切换为 JSON 目录时，需要上传新版 `index.html`、`assets/`、`reports.json`；现有研报目录不变。以后新增研报不改变首页和公共脚本，只更新目录 JSON 及相应报告文件。构建只把公开字段写入 JSON，不包含原稿路径和草稿。

## 一体化 Skill：研报分析与发布

已提供 `research-report-publish`，项目中保留可维护源文件 `skills/research-report-publish/`，安装副本位于 `~/.codex/skills/research-report-publish/`。以后上传 PDF 附件并调用：

> 使用 $research-report-publish 分析附件，按项目默认提示词生成 HTML，并增量发布。

只要生成本地文件时，改为“只生成，不发布”。默认分析提示词仍在 `prompts/研报单页HTML解读.md`，支持当次覆盖。重要数字应核对原报告，HTML 要验证手机阅读后才上传。

SSH 主机、端口、用户、本机私钥路径、站点根目录及 HTTP 地址保存在不进 Git 的 `deploy.local.json`。私钥内容不存入项目；部署前按自己的环境核对连接配置。

查看增量计划（不上传）：

```sh
python3 skills/research-report-publish/scripts/deploy.py
```

实际发布需在计划中逐一列明本次已授权的新增报告 ID：

```sh
python3 skills/research-report-publish/scripts/deploy.py --report 2026/新报告英文标识 --apply
```

多篇重复 `--report`。若还有其他本地待发布报告，先明确处理范围，脚本会拒绝遗漏授权 ID 的发布。已有线上报告和首页不会被该脚本改写；远端比本地多报告或元数据不一致时会停止，避免覆盖线上内容。

脚本会将新增目录设为 755、HTML/素材/JSON 设为 644；在站点外暂存并核对哈希，先落报告目录，最后原子替换 reports.json。最后验证 SSH 文件哈希与 HTTP JSON/HTML 内容；不使用 777，也不修改其他站点或用户主目录的权限。

部署事务的本地回归测试：`python3 tests/test_report_deploy.py`。此测试仅在临时本地目录运行，不修改线上站点。
