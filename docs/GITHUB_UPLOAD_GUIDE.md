# GitHub 上传教程（推荐先建 Private 仓库）

1. 下载 ZIP，解压获得 `glider-current-estimation-filtered` 文件夹。
2. 前往 https://github.com/new ，仓库名建议 `glider-current-estimation-filtered`，初始选 **Private**。
3. 不要让 GitHub 自动生成另一个 README 或 .gitignore，以免与现有文件冲突。
4. 在新仓库点击 `uploading an existing file`，上传解压后**文件夹内的文件和子目录**，而不是只上传 ZIP。
5. 核查根目录有 README.md、src、scripts、results、docs；不要出现 `QC` 目录、实验室的 Matlab 函数、私有原始数据。
6. 打开 README，核对三个结果图能加载，确认源文件只含下游筛选版 `src/filtered_cohort_analysis.py`。
7. 在仓库 Actions 检查验证脚本是否通过，或本地运行 `python scripts/verify_repository.py`。
8. 获得课题组对发布**汇总结果、图表和个人编写代码**的许可后，再在仓库 Settings 中把仓库调整为 Public。
9. 简历上添加形如 `https://github.com/你的用户名/glider-current-estimation-filtered` 的真实地址。

**提醒：** 项目总结的 223 个任务来自私有上游输入，不代表 GitHub 可公开从零跑出全部科研结果；切勿上传敏感原始数据来“凑齐复现”。
