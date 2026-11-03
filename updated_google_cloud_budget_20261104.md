# Google Cloud 预算只读核查（2026-11-04）

本机 `gcloud` 当前项目为 `dsa5208p`。只读命令 `gcloud billing projects describe dsa5208p` 返回 `billingEnabled: false`，关联的结算账号为“我的结算账号”；`gcloud billing accounts list` 返回该账号 `OPEN: False`。因此此项目**当前不能启动 Google Cloud GPU VM**，可用于本实验的即时云计算额度为零。没有创建实例、启用计费或更改结算设置。

`gcloud billing budgets list` 未能读取预算：项目没有启用 Cloud Billing Budget API。该接口未被启用。本次只读访问也无法获取促销赠金的剩余额度；项目停用计费和结算账号关闭不等于证明赠金数字为零。用户可在 Google Cloud Console 的 **Billing → My Billing Accounts** 清除“Active”筛选，打开“我的结算账号”，分别查看 **Credits** 的 Remaining value 和账号状态。官方说明见 [查看促销赠金](https://docs.cloud.google.com/billing/docs/how-to/resolve-issues)、[核对计费状态](https://docs.cloud.google.com/billing/docs/how-to/verify-billing-enabled)。

若将来启用付费结算，还须重新核对区域 GPU 配额和实例可用性；目前 `gcloud compute regions describe asia-southeast1` 也被“项目未启用 billing”拒绝，不能把旧配额数字当作当前值。Google Cloud Free Trial 对 GPU 有限制，使用 GPU 需符合付费账号条件，见 [Google Cloud Free Program](https://docs.cloud.google.com/free/docs/free-cloud-features)。普通预算提醒不会自动封顶费用，见 [Cloud Billing budgets](https://docs.cloud.google.com/billing/docs/how-to/budgets)。

若用 Cloud 做 4/8 GPU 扩展，必须在**同一种 Cloud GPU 环境**重新跑 1/2 GPU 基准，再和 4/8 构成一条曲线；Vanda A40 的 1/2 点与 Cloud L4/P4 的 4/8 点不能直接合并为硬件一致的强扩展。当前没有任何 Cloud 实测，也没有产生新 Cloud GPU 费用。
