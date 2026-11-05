# How to make your own cards

**Different AI models have different capabilities; the prompts and AI recommendations are for reference only.**

#### Preparation:

- Vocabulary list (a word may have multiple meanings. It is recommended to provide the meanings you want to learn for more targeted study. Providing multiple meanings for one word may affect the story quality. The specific result depends on the capabilities of the AI used.)
- Any conversational AI

#### Step 1: Generate a story

- Recommended models: GPT, Gemini, or DeepSeek

- Generate in batches; each batch should contain no more than 60 words.
- **Input:** the reference prompt + vocabulary list;
- **Output:** text in TXT format: one passage in the learning language and one corresponding translation in the native language. In the learning-language passage, mark each word using the format `{{word /pronunciation hint, such as phonetic transcription/ native-language meaning}}`; in the native-language translation paragraph, mark it with `**native-language meaning**`.
- Reference prompt:

```text
Native language: [Enter your native language]

Learning language: [Enter your target learning language]

Article difficulty and style: [Enter your exam goal, current level, and preferred style. Examples: xianxia fantasy, romance, or IELTS style]

1. Some words in the list may have definitions. Write the words below into a natural, coherent, memorable short story, and keep the language of the entire story consistent with the words.

2. A word may have multiple meanings. Strictly follow the corresponding definitions when writing the story. If n definitions are provided, the word must appear at least n times and include all of those meanings.

3. Use every word at least once and mark the target words according to the specified format.

4. After generating the story, check: does it contain every word and every definition?

5. Provide one passage in the learning language and one corresponding translation in the native language. Do not add numbering or headings such as “Learning language”; provide only the actual content. In the learning-language passage, mark words from the vocabulary list using the format `{{word /pronunciation hint, such as phonetic transcription/ native-language meaning}}`; in the native-language translation paragraph, mark them with `**native-language meaning**`.

6. Output: a TXT-format text that can be copied with one click.

**Words:** `Paste this batch of words here`
```



#### Step 2: Enhance the blanks with additional words

- Recommended model: for Chinese-English learning, DeepSeek is recommended

- Process unfamiliar words that may appear in the story to help with comprehension or expand memory.
- **Input:** the prompt + the bilingual passage copied from the previous step
- **Output:** mark words using the format `{{word /pronunciation hint, such as phonetic transcription/ +native-language meaning}}` (“+” indicates an additional word not included in the vocabulary list).

- Reference prompt:

```text
My vocabulary level: [For example: I know some common CET-4 vocabulary]

Native language: [Enter your native language]

Learning language: [Enter your target learning language]

Requirements:

1. Among the words not enclosed in {{}}, which ones might I not know? Mark them using the format `{{word /pronunciation hint, such as phonetic transcription/ +native-language meaning}}` (“+” indicates an additional word not included in the vocabulary list).

2. Determine the native-language meaning from the context.

3. Output: a TXT-format text that can be copied with one click, without the native-language translation paragraph.
```



#### Step 3: Organize the template file (Doubao recommended)

- **Input:** the prompt + the learning-language passage copied from the previous step (without the native-language translation)
- **Output:** mark words using the format `{{word /pronunciation hint, such as phonetic transcription/ +native-language meaning}}` (“+” indicates an additional word not included in the vocabulary list).

Reference prompt:

```text
1. Split the passage into paragraphs again, separating paragraphs with ===. The number of words / punctuation marks / characters in each paragraph must be between 350 and 500, including punctuation such as {{}} and /; it must never exceed 500 (this is the only paragraph-splitting criterion; do not consider semantic logic).

2. Do not split a complete sentence (for example, do not put part of one sentence in one paragraph and the rest in the next).

3. Before each output, check and ensure that no paragraph exceeds 500 characters.

4. Output a TXT-format text that can be copied with one click.
```

#### Step 4: Save the TXT text from Step 3 as a TXT file

