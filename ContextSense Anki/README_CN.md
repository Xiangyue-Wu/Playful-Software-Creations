# 语境多感记忆卡 / ContextSense Anki

[TOC]

**当前项目仅实测过 Win11 网页版、Android 10。**  
**如有问题，欢迎通过 [Issue](https://github.com/Xiangyue-Wu/Playful-Software-Creations/issues/new) 进行反馈。有空时会解决。**

## 1. 项目简介

- 研究表明，跨感官语义一致的事件通常能够被更好地记住 [1]。基于这一思路，本项目通过语境故事，同时调动听、说、读、写，帮助学习者更高效地记忆多语言词汇。对于需要**键盘拼写单词**的考试，尤其有效。

- 项目内置**雅思词汇**相关的语境故事卡片（持续更新中），并支持按模板上传**任意语言**的卡片文件。

- 网页和安卓版均支持中文/英文，可通过界面左上角的“语言设置”切换。

## 2. 安装与使用

本项目同时提供网页版和安卓版。

**网页版**使用浏览器TTS（推荐使用Chrome）。**安卓版**暂不支持发音。

### 2.1 网页版

下载 [最新版 ContextSenseAnki-Web.zip](https://github.com/Xiangyue-Wu/Playful-Software-Creations/releases/latest/download/ContextSenseAnki-Web.zip)，解压后打开其中的 `ContextSenseAnki.html` 即可使用。

旧版本保存在[历史发布](https://github.com/Xiangyue-Wu/Playful-Software-Creations/releases)中。更新时请在原文件夹替换网页文件，并继续使用相同浏览器及原来的 HTML 入口文件名，以保留原有浏览器数据位置。

本次网页版更新：新增易忘词速刷模式，修复网页版数据存储 bug。

网页数据保存在当前浏览器中；更换浏览器或设备时，请使用应用内的“备份数据”和“恢复数据”功能迁移学习进度。

网页版文件位于 [`Web/`](./Web/) 目录，内置卡片数据已包含在 `bundled-backup.js` 中。若未成功加载初始数据，可导入该文件

### 2.2 安卓版

- Android 10：[下载 ContextSense Anki Android 10 APK](https://github.com/Xiangyue-Wu/Playful-Software-Creations/releases/latest/download/ContextSenseAnki-Android10.apk)
- Android 11：[下载 ContextSense Anki Android 11 APK](https://github.com/Xiangyue-Wu/Playful-Software-Creations/releases/latest/download/ContextSenseAnki-Android11.apk)

下载对应版本的 APK 后，在安卓设备上安装即可。安卓版源码与内置数据位于 [`Android/ContextSenseAnki-Android-Project/`](./Android/ContextSenseAnki-Android-Project/)。

### 2.3 主要按钮简介

#### 1.组合模式（推荐初学使用）

可设置“连续记住多少次后标记为 `known`”以及每组卡片数量。先学习句子卡片；一组卡片全部掌握后，自动进入该组的熟词复习，适合循序渐进地建立记忆。

#### 2.易忘词（推荐复习使用）

按单词/词组累计遗忘次数从高到低排列，优先复习最容易忘记的内容。学习过程中会持续更新遗忘次数，并保存中途退出时的进度。

#### 3.复习熟词

从已标记为 `known` 的句子卡片中提取被遮挡的单词/词组，随机组成速刷卡片。若标记遗忘，会回到该单词所属的原句子卡片进行针对性复习。

#### 4.继续 / 学习

“学习”开始新的学习会话；如果已有未完成会话，按钮会显示“继续”，可从上次退出的位置恢复。学习进度会自动保存，浏览器异常关闭也不会主动清空记录。

#### 5.速刷模式

熟词复习和易忘词复习都属于速刷模式：一次标记记住即可完成当前单词，适合快速大量重复，加深记忆。

易忘词弹窗右上角新增“速刷模式”，与“开始组合模式”共享复习进度。第一次左键显示详情，再次左键记住；右键遗忘并累计遗忘次数。每轮每词只出现一次，结束显示记住/遗忘统计及最新易忘词列表；Tab 可撤销标记。

## 4. 卡片模板说明与制作

### 4.1 模板说明

每张卡片用 `===` 分隔；需要遮挡的内容放在双花括号中，例如：

```text
There is a {{beautiful /ˈbjuːtɪfl/ 美丽的}} garden.
===
This is the next {{card /kɑːd/ 卡片}}.
```

花括号内使用 `/` 分隔“单词/词组”和音标、中文等详情。上传后，单词/词组可直接进行键盘拼写练习。

### 4.2 制作自己的卡片——模板整理流程与参考提示词

#### 1.获取txt文件

- 文本处理消耗额度不少，若你有额度充足、可直接编辑本地文件的AI（OpenCode、Codex、ClaudeCode），直接发送：

  ```tex
  1.忽略./How to make your own cards/如何制作你自己的卡片.md中的模型推荐，直接根据其中的提示词，分步为制作txt文件
  
  2.输入：[单词表文件路径]
  
  3.输出：同目录下新建MyStoriesContextSenseAnki，保存输出的txt文件
  ```

- 若你额度不充足或没有那样的助手，免费的网页对话AI完全可处理。只需三步复制粘贴。

  自行阅读：[如何制作你自己的卡片](./How%20to%20make%20your%20own%20cards/%E5%A6%82%E4%BD%95%E5%88%B6%E4%BD%9C%E4%BD%A0%E8%87%AA%E5%B7%B1%E7%9A%84%E5%8D%A1%E7%89%87.md)

  （点击上方链接即可跳转至中文制作说明。）

#### 2.导入网页/设备

通过“增加卡片”按钮，导入txt

## 5. 项目目录

```text
Web/
  ContextSenseAnki.html
  ContextSenseAnki-Web.zip
  app.js
  styles.css
  bundled-backup.js
Android/
  ContextSenseAnki-Android10.apk
  ContextSenseAnki-Android11.apk
  ContextSenseAnki-Android-Project/
README_CN.md
README_EN.md
```

## 6. 参考文献

[1] Soto-Faraco & Spence (2025), *Psychological Bulletin*. [DOI: 10.1037/bul0000483](https://doi.org/10.1037/bul0000483?utm_source=chatgpt.com)
