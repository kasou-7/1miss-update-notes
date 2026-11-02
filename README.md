# 1miss · osu! 更新中文记录

为 1miss 提供公开的 osu! Stable、lazer 及官方测试版更新译文。用户无需注册翻译服务、填写密钥或自建服务器。

- `main`：翻译生成与发布脚本、固定版本依赖和 GitHub Actions 工作流。
- `update-translations`：`zh-Hans.json`、公开文本翻译缓存和最近运行记录。
- 每 6 小时尝试检查新增或变更的更新记录；可在 Actions 页面手动运行，维护脚本更新时也会触发。
- 默认简体中文，保护 miss、great、Mod 名称与缩写等 osu! 术语；版本、作者、代码与原文链接保留。
- 每版译文绑定原文 SHA-256。内容变更或译文未完成时，1miss 保留原文与已缓存的译文。

## 客户端读取地址

https://raw.githubusercontent.com/kasou-7/1miss-update-notes/refs/heads/update-translations/zh-Hans.json

1miss 0.4.8 已预留这个地址，无需再次修改软件读取路径。仓库只公开更新记录、翻译缓存和维护脚本，不包含应用主源码、账号配置、用户记录或密钥。

## 翻译方式

使用 DeepL 免登录交互端点，并非官方开发者 API，服务可用性不保证。任务使用保守批量和间隔，遇到拒绝或限流停止；下次任务再检查。OpenCC 0.1.7 仅用于生成时的简体校正，固定依赖 SHA-256，不要求软件用户安装。

GitHub Actions 使用自动提供的临时令牌发布数据分支，无需个人 Secrets。定时任务可能延迟；若 GitHub 因长期无活动停用，可在 Actions 中重新启用。原始更新、贡献者署名和商标归 osu! 及各权利人；机器译文为非官方翻译。

原文：[osu! 更新日志](https://osu.ppy.sh/home/changelog) · [ppy/osu Releases](https://github.com/ppy/osu/releases)
