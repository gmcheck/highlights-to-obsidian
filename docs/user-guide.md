# Highlights to Obsidian 用户使用说明

## 目录

1. [插件简介](#插件简介)
2. [安装与卸载](#安装与卸载)
3. [快速入门](#快速入门)
4. [配置详解](#配置详解)
   - [Formatting（格式化）选项卡](#formatting格式化选项卡)
   - [Vault（库设置）选项卡](#vault库设置选项卡)
   - [Advanced（高级选项）选项卡](#advanced高级选项选项卡)
5. [模板语法参考](#模板语法参考)
6. [发送功能说明](#发送功能说明)
7. [常见问题](#常见问题)

---

## 插件简介

**Highlights to Obsidian** 是一款 Calibre 插件，用于将电子书阅读过程中的高亮和批注同步到 Obsidian 笔记软件中。

### 核心特性

- **两种发送模式**：URI 模式和 Direct Write 模式
- **自定义模板**：灵活定义笔记格式
- **智能排序**：按位置、时间、章节等排序
- **增量发送**：只发送新增高亮
- **一键跳转**：从笔记直接跳转到 Calibre 原文

---

## 安装与卸载

### 安装步骤

1. 下载插件 ZIP 包（从 GitHub Releases 或其他来源）
2. 打开 Calibre，点击菜单「首选项」
3. 在「高级」部分点击「插件」
4. 点击右下角「从文件加载插件」按钮
5. 选择下载的 ZIP 文件
6. 重启 Calibre 完成安装

### 卸载步骤

1. 打开「首选项 → 插件」
2. 在插件列表中找到「Highlights to Obsidian」
3. 右键点击，选择「移除插件」
4. 重启 Calibre

---

## 快速入门

### 基本使用流程

1. **配置插件**
   - 点击工具栏插件图标
   - 选择「Open Configuration」打开配置窗口
   - 配置 Obsidian 库路径和发送模式

2. **阅读并高亮**
   - 在 Calibre 阅读器中打开电子书
   - 选择文本，添加高亮和批注

3. **发送到 Obsidian**
   - 在 Calibre 书库列表中选中一本书
   - 点击工具栏 H2O 图标，自动发送选中书籍的新高亮
   - 或点击下拉箭头选择其他发送方式

### 推荐配置（Direct Write 模式）

对于整书精读场景，推荐使用 Direct Write 模式：

1. 在「Vault & Direct Write」选项卡中：
   - 勾选「Enable direct write into vault」
   - 填写 Obsidian 库的绝对路径
   - 设置「Sort key」为 `location`

2. 在「Formatting」选项卡中：
   - 根据需要调整模板格式

---

## 配置详解

配置窗口包含三个选项卡：Formatting、Vault、Advanced。

### Formatting（格式化）选项卡

此选项卡用于自定义笔记的格式模板。

#### 变量参考

点击「▶ 显示变量参考」可展开/折叠变量列表。变量列表仅作参考，不影响配置。

#### 条件块语法

模板支持条件块语法，用于控制内容的有条件显示：

```
{if_notes}
### 我的思考

{notes_quoted}
{end_if_notes}
```

- `{if_notes}...{end_if_notes}`：仅当高亮有批注时，才显示其中的内容
- 无批注时，整个条件块（包括标记）会被完全移除

**示例**：默认模板中，"我的思考"部分使用条件块包裹，无批注时不会显示空标题。

#### Note title format（笔记标题格式）

定义生成的笔记文件名，支持使用 `/` 创建子目录。

**默认值**：
```
学习/Books/{title} by {authors}
```

**示例**：
- `{title}` → `三体.md`
- `{title} by {authors_str}` → `三体 by 刘慈欣.md`
- `读书笔记/{year}/{title}` → `读书笔记/2024/三体.md`

**注意事项**：
- 文件名中的 `/` 会自动创建子目录
- 不支持 Windows 非法字符（如 `:`, `*`, `?` 等）

#### Note body format（笔记正文格式）

定义每条高亮的格式。支持条件块语法。

**默认值**：
```
---
## 高亮记录 | {chapter} | {localdate} {localtime}
> [!quote] 原文高亮
{blockquote}

^{highlight_id}

[📖 一键跳回Calibre原文]({url})

{if_notes}
### 我的思考

{notes_quoted}
{end_if_notes}
```

**说明**：
- `---` 用于分隔多条高亮
- `^{highlight_id}` 创建 Obsidian 块引用（阅读模式下自动隐藏）
- `{notes_quoted}` 会自动处理批注中的空行
- `{if_notes}...{end_if_notes}` 确保无批注时不显示"我的思考"标题

#### 笔记头部模板（Note header format）

**重要**：此模板仅在新建笔记时添加一次，适合放置 YAML front matter。

**默认值**：
```yaml
---
tags: [books]
book: "《{title}》"
author: "{authors_str}"
---
# 《{title}》读书笔记
```

**可用变量**：
- `{title}` - 书籍标题
- `{authors_str}` - 作者字符串

**使用场景**：
- 添加 Obsidian 标签
- 添加书籍元数据
- 添加笔记标题

#### 恢复默认模板按钮

点击「恢复默认模板」按钮可将正文格式和笔记头部模板恢复为默认值（标题格式除外）。

---

### Vault（库设置）选项卡

此选项卡配置 Obsidian 连接、发送模式和排序。

#### 发送模式对比

| 特性 | URI 模式 | Direct Write 模式 |
|------|----------|-------------------|
| 新建笔记 | ✅ 支持 | ✅ 支持 |
| 追加到现有笔记 | ❌ 不支持 | ✅ 支持 |
| 前置到现有笔记 | ❌ 不支持 | ✅ 支持 |
| 需要 Obsidian 运行 | ✅ 需要 | ❌ 不需要 |
| 后台静默写入 | ❌ 会切换窗口 | ✅ 支持 |
| 权限要求 | 无 | 需要库文件夹读写权限 |

**推荐**：整书精读、多次高亮汇总 → 使用 Direct Write 模式

#### 基本设置

##### Obsidian vault name（URI 模式）

填写 Obsidian 库的名称，用于 URI 模式发送。

**示例**：如果库路径是 `D:\Obsidian\MyNotes`，则填写 `MyNotes`。

**注意**：仅在 URI 模式下生效，Direct Write 模式不需要此项。

##### Obsidian vault absolute path（Direct Write 模式）

填写 Obsidian 库的绝对路径。

**示例**：
- Windows: `D:\Obsidian\MyNotes`
- macOS: `/Users/username/Obsidian/MyNotes`
- Linux: `/home/username/Obsidian/MyNotes`

**注意**：确保路径正确，否则写入会失败。

##### Enable direct write into vault

勾选后启用 Direct Write 模式，取消则使用 URI 模式。

#### Direct Write 选项

以下选项仅在 Direct Write 模式下可用：

##### Open note in Obsidian after write

写入完成后自动在 Obsidian 中打开笔记。

**适用场景**：希望立即查看笔记效果时勾选。

##### PREPEND new content (uncheck to APPEND)

- **勾选**：新内容插入到笔记开头（前置模式）
- **不勾选**：新内容追加到笔记末尾（追加模式，默认）

**推荐**：追加模式配合 `location` 排序，高亮按书籍顺序排列。

#### 排序设置

##### Sort key（排序键）

定义同一批次发送的高亮的排序方式。

**可选值**：

| 值 | 说明 | 推荐场景 |
|----|------|----------|
| `location` | 按书籍中的位置排序 | 整书精读，保持原文顺序 |
| `timestamp` | 按高亮创建时间排序 | 按阅读进度记录 |
| `date` | 按高亮日期排序 | 按天整理笔记 |
| `time` | 按高亮时间排序 | 同一天内的排序 |
| `chapter` | 按章节标题排序 | 按章节分组 |

**推荐值**：`location`

**注意**：排序仅对同一批发送的高亮生效。如果分多次发送，每次发送的内容会按设置追加/前置到笔记中。

---

### Advanced（高级选项）选项卡

#### 笔记设置

##### Maximum note size（最大笔记大小）

设置单个笔记文件的最大大小（字符数），超过时会自动分割。

- `0` = 无限制
- 默认值：`20000`

**适用场景**：防止笔记文件过大影响 Obsidian 性能。

##### Include header in each split note

当笔记因超过大小限制而分割时，是否在每个分割后的笔记中包含头部。

#### 发送设置

##### Last send time（上次发送时间）

显示上次发送高亮的时间。此时间用于「Send new highlights」功能判断哪些是新高亮。

点击「Now」按钮可将时间重置为当前时间。

**使用场景**：如果想重新发送所有高亮，可以将时间设置为较早的日期。

##### Time to wait between sends（发送间隔时间）

设置批量发送时，每次发送之间的等待时间（秒）。

**默认值**：`0.1`

**适用场景**：如果遇到发送失败，可以适当增加此值。

#### 界面选项

##### Confirm before sending all highlights

发送所有高亮前是否显示确认对话框。

**推荐**：勾选，防止误操作。

##### Show count after sending

发送完成后是否显示发送数量统计。

**推荐**：勾选，方便确认发送结果。

#### Web 用户设置

用于多人共用 Calibre 时区分各自的高亮。勾选「Send web user's highlights」后启用用户名输入。

##### Web username

设置 Web 用户名，用于区分不同用户的高亮。

**默认值**：`*`（匹配所有用户）

#### 调试

##### Use xdg-open (Linux only)

仅 Linux 系统可用。使用 xdg-open 命令打开链接。

##### Enable file logging

启用文件日志记录，用于调试问题。

**日志位置**：`<Obsidian库路径>/h2o_debug.log`

**适用场景**：遇到问题时启用，方便排查。

---

## 模板语法参考

### 书籍信息变量

| 变量 | 说明 | 类型 |
|------|------|------|
| `{title}` | 书籍标题 | 字符串 |
| `{authors}` | 作者列表 | 元组 |
| `{authors_str}` | 作者（逗号分隔） | 字符串 |
| `{bookid}` | Calibre 书籍 ID | 整数 |

### 高亮内容变量

| 变量 | 说明 | 示例输出 |
|------|------|----------|
| `{highlight}` | 高亮原文 | 生存是文明的第一需要 |
| `{highlight_text}` | 同 highlight | 生存是文明的第一需要 |
| `{blockquote}` | 引用块格式 | > 生存是文明的第一需要 |
| `{callout_quote}` | Obsidian callout | > [!quote] 生存是文明的第一需要 |
| `{notes}` | 批注原文 | 这是费米悖论的核心 |
| `{notes_quoted}` | 批注引用块 | > 这是费米悖论的核心 |

### 位置与链接变量

| 变量 | 说明 |
|------|------|
| `{url}` | 跳转到 Calibre 的链接 |
| `{location}` | CFI 位置标识 |
| `{chapter}` | 章节标题 |
| `{uuid}` | 高亮完整 UUID |
| `{highlight_id}` | 短 ID（8位） |

### 时间变量

| 变量 | 说明 | 时区 |
|------|------|------|
| `{timestamp}` | Unix 时间戳 | UTC |
| `{date}` | 日期 | UTC |
| `{time}` | 时间 | UTC |
| `{datetime}` | 日期时间 | UTC |
| `{localdate}` | 日期 | 本地 |
| `{localtime}` | 时间 | 本地 |
| `{localdatetime}` | 日期时间 | 本地 |
| `{datenow}` | 当前日期 | 本地 |
| `{timenow}` | 当前时间 | 本地 |
| `{utcnow}` | 当前 UTC 时间 | UTC |
| `{year}` | 年份 | UTC |
| `{month}` | 月份 | UTC |
| `{day}` | 日期 | UTC |
| `{hour}` | 小时 | UTC |
| `{minute}` | 分钟 | UTC |
| `{second}` | 秒 | UTC |

### 统计变量

| 变量 | 说明 |
|------|------|
| `{totalsent}` | 累计发送高亮总数 |
| `{booksent}` | 本书累计发送高亮数 |
| `{highlightsent}` | 本次发送高亮数 |

---

## 发送功能说明

插件在 Calibre 工具栏中显示为 H2O 图标。

### 默认行为

**点击图标**：直接发送选中书籍的新高亮（等同于 "Send New (Selected Books)"）。

**下拉菜单**：点击图标旁的下拉箭头，可访问完整菜单。

### 菜单说明

#### 高频操作

| 菜单项 | 说明 |
|--------|------|
| **Send New Highlights** | 发送所有书籍的新高亮（上次发送时间之后新增的）。发送后会更新「Last send time」。 |
| **Send New (Selected Books)** | 仅发送 Calibre 列表中选中书籍的新高亮。**不会**更新「Last send Time」，未选中书籍的新高亮不受影响，后续仍可通过 "Send New Highlights" 发送。 |

#### 低频操作

| 菜单项 | 说明 |
|--------|------|
| **Send All Highlights** | 发送所有书籍的全部高亮。操作前会弹出确认对话框。 |
| **Send All (Selected Books)** | 发送选中书籍的全部高亮。操作前会弹出确认对话框。 |
| **Resend Last Sent** | 重发上次发送的高亮。主要用于 Obsidian 未成功接收时的重试。 |

#### 辅助操作

| 菜单项 | 说明 |
|--------|------|
| **Config** | 打开配置窗口 |
| **Help** | 显示帮助信息 |

### 发送逻辑详解

#### "Send New" 与 "Send New (Selected Books)" 的区别

假设书 A、书 B 都有新高亮：

| 操作 | 书 A | 书 B | 更新 Last Send Time |
|------|------|------|---------------------|
| Send New Highlights | ✅ 发送 | ✅ 发送 | ✅ 是 |
| Send New (Selected Books)，选中书 A | ✅ 发送 | ❌ 不发送 | ❌ 否 |

**关键区别**："Send New (Selected Books)" 不会更新 `last_send_time`，因此书 B 的新高亮不会丢失，后续仍可通过 "Send New Highlights" 发送。

#### 增量发送原理

插件通过 `last_send_time` 记录上次发送时间。"Send New" 只发送高亮创建时间晚于 `last_send_time` 的高亮。

如果需要重新发送所有高亮，可以在配置窗口的「Other Options」选项卡中点击「Now」按钮重置时间。

---

## 常见问题

### Q: 发送后笔记中没有内容？

**可能原因**：
1. Obsidian 库路径配置错误
2. 没有写入权限
3. 模板格式有误

**解决方法**：
1. 检查「Obsidian vault absolute path」是否正确
2. Windows 用户尝试以管理员身份运行 Calibre
3. 启用「Enable file logging」查看日志

### Q: 高亮顺序不对？

**解决方法**：
1. 检查「Sort key」设置，推荐使用 `location`
2. 注意排序仅对同一批发送的高亮生效

### Q: 时间显示不正确（差8小时）？

**原因**：使用了 UTC 时间变量。

**解决方法**：使用本地时间变量，如 `{localdate}` 替代 `{date}`，`{localtime}` 替代 `{time}`。

### Q: Windows 出现写入权限报错？

**解决方法**：右键 Calibre 选择「以管理员身份运行」。

### Q: 笔记头部模板没有生效？

**可能原因**：
1. 笔记文件已存在（头部只在新建时添加）
2. 模板为空或格式有误

**解决方法**：删除现有笔记后重新发送，或手动添加头部内容。

### Q: 批注中的空行导致格式混乱？

**解决方法**：使用 `{notes_quoted}` 变量而非 `{notes}`，它会自动处理空行格式。

### Q: 如何重新发送所有高亮？

**方法**：
1. 打开配置窗口
2. 在「Other Options」选项卡中点击「Now」按钮重置时间
3. 或者删除 Obsidian 中的笔记文件后重新发送

---

## 技术支持

如遇到问题，请：
1. 启用「Enable file logging」
2. 查看日志文件：`<Obsidian库路径>/h2o_debug.log`
3. 在 GitHub 提交 Issue 并附上日志信息
