# ContextSense Anki / 语境多感记忆卡

[TOC]

**This project has only been tested on the Windows 11 web version and Android 10.**  
**If you encounter any problems, please submit feedback through an [Issue](https://github.com/Xiangyue-Wu/Playful-Software-Creations/issues/new). I will address it when I have time.**

## 1. Project overview

- Research shows that crossmodally congruent events are usually remembered better [1]. Based on this idea, this project uses contextual stories to engage listening, speaking, reading, and writing at the same time, helping learners remember multilingual vocabulary more efficiently. It is especially effective for exams that require **keyboard-based word spelling**.

- The project includes contextual story cards related to **IELTS vocabulary** (continuously updated) and supports uploading card files in **any language** according to the template.

- Both the web and Android versions support Chinese and English. You can switch languages through “Language settings” in the upper-left corner.

## 2. Installation and use

Both web and Android versions are provided.

The **web version** uses browser TTS (Chrome is recommended). The **Android version** does not currently support pronunciation.

### 2.1 Web version

Download the [latest ContextSenseAnki-Web.zip](https://github.com/Xiangyue-Wu/Playful-Software-Creations/releases/latest/download/ContextSenseAnki-Web.zip), extract it, and open `ContextSenseAnki.html`.

Previous versions remain available in [Releases](https://github.com/Xiangyue-Wu/Playful-Software-Creations/releases). When updating, replace the web files in their original folder and continue using the same browser and HTML entry filename to retain the existing browser data location.

Web update: Added quick review mode for difficult words and fixed a data persistence bug in the web version.

Web data is saved in the current browser. If you change browsers or devices, use the in-app “Backup data” and “Restore data” functions to transfer your learning progress.

The web files are located in the [`Web/`](./Web/) directory. Built-in card data is included in `bundled-backup.js`. If the initial data does not load successfully, you can import this file.

### 2.2 Android version

- Android 10: [Download ContextSense Anki Android 10 APK](https://github.com/Xiangyue-Wu/Playful-Software-Creations/releases/latest/download/ContextSenseAnki-Android10.apk)
- Android 11: [Download ContextSense Anki Android 11 APK](https://github.com/Xiangyue-Wu/Playful-Software-Creations/releases/latest/download/ContextSenseAnki-Android11.apk)

Download the APK for the corresponding Android version and install it on your device. The Android source code and built-in data are located in [`Android/ContextSenseAnki-Android-Project/`](./Android/ContextSenseAnki-Android-Project/).

### 2.3 Main buttons

#### 1. Combination mode (recommended for beginners)

You can set how many consecutive “remember” actions are required before a card is marked as `known`, as well as the number of cards in each group. Study sentence cards first; after all cards in a group have been mastered, the app automatically starts a review of the known words from that group. This is suitable for building memory step by step.

#### 2. Forgettable words (recommended for review)

Words and phrases are sorted by accumulated forget count from highest to lowest, prioritizing the content that is easiest to forget. Forget counts are updated continuously during learning, and progress is saved when you leave in the middle of a session.

#### 3. Review known words

Masked words and phrases are extracted from sentence cards marked as `known` and randomly arranged into rapid-review cards. If an item is marked as forgotten, the app returns to the original sentence card containing that word for targeted review.

#### 4. Continue / Learn

“Learn” starts a new learning session. If an unfinished session already exists, the button displays “Continue” and resumes from the position where you last left off. Learning progress is saved automatically, and an unexpected browser close does not actively clear the records.

#### 5. Rapid-review mode

Review known words and forgettable words are both rapid-review modes: one “remember” action completes the current word, making it suitable for quickly repeating many items and strengthening memory.

The new “Quick review” button in the difficult-word dialog shares progress with combination mode. Press Left to reveal details, Left again to remember, or Right to forget and increment the forget count. Each word appears once per round, followed by remember/forget totals and the updated difficult-word list. Tab undoes the last mark.

## 4. Card template instructions and creation

### 4.1 Template instructions

Separate each card with `===`; put the content to be masked inside double curly braces, for example:

```text
There is a {{beautiful /ˈbjuːtɪfl/ 美丽的}} garden.
===
This is the next {{card /kɑːd/ 卡片}}.
```

Inside the braces, use `/` to separate the “word/phrase” from pronunciation, Chinese meaning, and other details. After uploading, the word/phrase can be practiced directly by keyboard spelling.

### 4.2 Make your own cards — template organization workflow and reference prompts

#### 1. Obtain a TXT file

- Text processing consumes a considerable amount of quota. If you have an AI assistant with sufficient quota that can directly edit local files (OpenCode, Codex, ClaudeCode), send it the following directly:

  ```text
  1. Ignore the model recommendations in ./How to make your own cards/How to make your own cards.md and directly follow its prompts to create the TXT file step by step
  
  2. Input: [path to the vocabulary-list file]
  
  3. Output: create MyStoriesContextSenseAnki in the same directory and save the generated TXT files there
  ```

- If you do not have sufficient quota or do not have an assistant like that, a free web-based conversational AI can handle the task. You only need to copy and paste three times.

  Read: [How to make your own cards](./How%20to%20make%20your%20own%20cards/How%20to%20make%20your%20own%20cards.md)

#### 2. Import into the web app/device

Use the “Add cards” button to import the TXT file.

## 5. Project layout

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

## 6. Reference

[1] Soto-Faraco & Spence (2025), *Psychological Bulletin*. [DOI: 10.1037/bul0000483](https://doi.org/10.1037/bul0000483?utm_source=chatgpt.com)
