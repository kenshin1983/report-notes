# 研报生成提示词

将常用提示词保存在这里，例如 `行业研报.md`、`公司研究.md`。

现有模板：[研报单页 HTML 解读](研报单页HTML解读.md)，用于将 PDF 核心内容浓缩为支持手机、电脑及一键截图的简体中文单页。

每次让助手生成时，请明确：

- 原稿路径：`originals/YYYY/MM/原稿.pdf`
- 使用的提示词及输出语言、结构要求。
- 输出路径：`reports/YYYY/英文标识/index.html`
- 同步更新相邻的 `meta.json`，核对后设 `published: true`。
- 运行 `python3 scripts/build.py --zip` 更新 reports.json 目录数据和上传包。

HTML 应可独立访问、支持手机；优先把样式和脚本内嵌。外部素材放同目录 `assets/`，使用 `assets/xxx` 相对路径。返回列表用 `../../../index.html`。不把原稿链接、内部路径或其他私有内容写进公开页面。价格和观点注明原报告日期，不虚构原稿未提供的信息。

新增研报时保持首页 HTML 不变；交付时列出新增报告目录和 `dist/reports.json`，供用户增量上传。
