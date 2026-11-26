# net_auth

中科院计算所校园网（`gw.ict.ac.cn`，深澜 SRun 认证）命令行登录工具。

- 纯 HTTP 请求实现，**零第三方依赖**，单文件，Python ≥ 3.6
- 未认证时 IPv6 可用，可直接通过 PyPI 安装

## 安装

```bash
pip install ictgw-auth
```

也可以不安装，直接拷贝 `net_auth.py` 到目标机器运行：`python3 net_auth.py`。

## 使用

```bash
net_auth
```

- 未登录：提示输入账号和密码（密码不回显、不保存），登录后显示账号信息；
- 已登录：显示账号、IP、已用流量、已用时长，并询问是否退出登录（默认 `N`，保持登录）。

## 发布

推送形如 `v1.0.0` 的 tag 后，GitHub Actions 会自动构建并通过 Trusted Publishing 发布到 PyPI，版本号取自 tag。

## 致谢

本项目基于 [jklincn/ict_auth](https://github.com/jklincn/ict_auth)（MIT）改写：将 Playwright 无头浏览器方案替换为直接调用深澜认证接口。
