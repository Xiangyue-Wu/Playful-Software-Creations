Android 10 记忆卡片 APK 工程

包名：com.memorize.anki
版本：1.21（versionCode 22）
最低系统：按构建参数选择 Android 10（API 29）或 Android 11（API 30）
应用类型：完全离线 WebView 应用
预置数据：assets/bundled-backup.js（首次启动自动载入）

APK 只打包 index.html、styles.css、app.js、预置备份数据和 Android 外壳；
不会打包使用说明、测试文本或旧的 TXT 词库。

Android 版通过系统文件选择器恢复 JSON，并通过系统保存界面导出备份。
检测到旧版本遗留的空数据时，会自动恢复一次 APK 内置数据。
导出生词也通过系统保存界面导出 TXT；弹窗包含 Android 10 WebView 兼容样式。
学习界面的方向键与 Tab 均支持屏幕点击和外接键盘；单词卡的上下键控制详情显示。
学习按键操作不显示浮动提示；Android 返回键在学习页返回主页、在弹窗中关闭弹窗。
单词卡首次默认居中；手动调整后按横屏、竖屏分别记忆位置，连续单词卡及句子卡返回后都会恢复该位置。
实体键盘连接时，句子拼写框和卡片编辑框均不弹出屏幕键盘；未连接时照常自动弹出。
卡片编辑框聚焦时不截获实体键盘方向键，可直接使用方向键移动输入光标。
进入软件或从任意学习、完成界面返回主页时，首个已导入文件会自动显示在屏幕最上方。
实体键盘空格在拼写框内可输入词组；非输入状态下每次下滑约三分之二屏，Shift+空格向上滚动。
实体键盘 Tab 与屏幕 Tab 一样撤销上一次标记，并兼容 Android WebView 的 Unidentified 键名。
Android 原生层兼容标准键码、Unicode、扫描码和 ACTION_MULTIPLE 形式的 Space/Tab 快捷键。
实体键盘连接且输入框聚焦时，字母、数字、Shift/CapsLock 组合、标点和空格均由同一个
Unicode 读取函数与同一个当前光标写入函数处理；对应的按下、重复和抬起事件统一去重。
Ctrl/Meta 快捷键、AltGr 和死键组合得到保留；退格、回车和光标移动继续使用系统行为。
此时暂停 WebView 输入法连接，防止输入法再次缓存同一字符；失焦或拔出实体键盘后立即恢复。
软键盘仍使用 Android WebView 标准输入连接，实体键盘连接时由原生窗口策略隐藏软键盘。
“编辑”弹窗的文本区域在 Android 层完全绕过上述句子填空兼容逻辑，始终是标准 Android WebView 文本框；
字母、数字、符号、空格、Shift、输入法切换、选区、删除、回车和光标移动全部交由系统处理。
学习界面的句子填空框只接受 ASCII 可见字符、拉丁字母及常用英文排版符号；
中文等非英文字符会在输入前被阻止，并在系统组合输入漏过时立即清除，不影响整卡编辑框输入中文。

build-apk.ps1 -AndroidVersion 10 或 11 会使用 Android 官方命令行工具编译、对齐并签名 APK，
分别在本工程目录生成 ContextSenseAnki-Android10.apk 和 ContextSenseAnki-Android11.apk。
构建前请在系统中安装 JDK，并设置 JAVA_HOME；脚本不依赖特定电脑上的固定路径。
