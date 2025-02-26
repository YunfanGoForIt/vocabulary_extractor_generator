import os
import base64
import time
from openai import OpenAI
from pathlib import Path
import re
import csv

client = OpenAI(
    api_key=" ---- ",
    base_url="https://api.moonshot.cn/v1",
)

def rename_images_in_folder(folder_path):
    # 获取文件夹中的所有文件
    files = os.listdir(folder_path)
    # 过滤出图片文件
    image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
    
    # 按文件名排序
    image_files.sort()
    
    # 存储已经输出过的单词
    seen_words = set()  # 使用集合来存储单词，自动去重

    for i, filename in enumerate(image_files, start=1):
        old_file = os.path.join(folder_path, filename)
        # 获取文件扩展名
        file_extension = os.path.splitext(filename)[1]
        new_file = os.path.join(folder_path, f"{i}{file_extension}")
        os.rename(old_file, new_file)
        print(f"Renamed: {old_file} to {new_file}")

        # 对图片进行base64编码
        with open(new_file, 'rb') as f:
            img_base = base64.b64encode(f.read()).decode('utf-8')

        # 构建上下文，包含已经输出过的单词
        context = f"""

## 技能: 处理PPT图片并提取符合要求的单词
1. 用户提供大二课程分子与细胞（全英语）的课程PPT图片后，识别图片文本内容，但不要输出。
2. 总结该页PPT的主题，但不要输出。
3. 从识别出的文本中提取具有如下要求的英语专业名词：
    （1）关于生物或化学的
    （2）英语四级难度以上的，不要太简单
    （3）提取数量不超过8个
4. 将提取出的单词以英语逗号为间隔输出，并且都转化为小写。输出示例："conformation, substrate, enzyme, bonding"



## 限制:
- 仅围绕大二课程分子与细胞（全英语）的PPT内容进行处理和提取单词，不涉及其他无关主题。
- 不要输出除了提取的单词以外的任何内容。
- 仔细检查单词是否符合要求（1）关于生物或化学的（2）英语四级难度以上的，不要太简单（3）提取数量不超过8个
- 请不要重复输出以下单词(开头大写和不大写算作同一个单词，都不要再次出现）：{', '.join(seen_words)}
"""

        response = client.chat.completions.create(
            model="moonshot-v1-32k-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_base}"
                            }
                        },
                        {
                            "type": "text",
                            "text": context
                        }
                    ]
                }
            ]
        )

        # 存储每次大模型的回答
        response_content = response.choices[0].message.content
        print(response_content)
        print(context)

        # 将提取的单词添加到集合中
        new_words = response_content.split(', ')
        seen_words.update(new_words)

        time.sleep(3)

    # 将所有不重复的单词写入txt文件
    with open('all_words.txt', 'w') as f:
        f.write(', '.join(seen_words))
    print(seen_words)
    return seen_words

# 使用示例
folder_path = 'E:/文档/重要文档/2025.2/Ch 3'
words = rename_images_in_folder(folder_path)

print("All words have been written to all_words.txt")



# 读取 all_words.txt 文件中的内容
with open('all_words.txt', 'r') as f:
    words_content = f.read()

# 将内容按逗号分割成单词列表
words_list = words_content.split(', ')

# 对单词列表进行排序
sorted_words_list = sorted(words_list)

# 将排序后的单词列表写回 all_words.txt 文件
with open('all_words.txt', 'w') as f:
    f.write(', '.join(sorted_words_list))

print("Words have been sorted and written back to all_words.txt")

file_object = client.files.create(file=Path("E:/文档/重要文档/2025.2/单词表api/all_words.txt"), purpose="file-extract")

# 获取结果
# file_content = client.files.retrieve_content(file_id=file_object.id)
# 注意，之前 retrieve_content api 在最新版本标记了 warning, 可以用下面这行代替
# 如果是旧版本，可以用 retrieve_content
file_content = client.files.content(file_id=file_object.id).text

# 把它放进请求中
messages = [
    {
        "role": "system",
        "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一切涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
    },
    {
        "role": "system",
        "content": file_content,
    },
    {"role": "user", "content": """
将文件中的单词一个一个详细列出单词表，包含词性（如n. v.)、音标和中文释义，以markdown格式代码块输出，方便复制到markdown编辑软件。完整输出，不要中断，不要输出除了markdown代码块以外的内容。
格式如下：
| 单词 | 词性 | 音标 | 释义 |
| ---- | ---- | ---- | ---- |
| [具体单词] | [词性] | [音标] | [释义] |
"""
},
]

# 然后调用 chat-completion, 获取 Kimi 的回答
response_2 = client.chat.completions.create(
    model="moonshot-v1-32k",
    messages=messages,
    temperature=0.3,
    max_tokens=11800,
)

print(response_2.choices[0].message.content)
# 存储每次大模型的回答
response_content = response_2.choices[0].message.content

def extract_markdown_block(response):


    # 查找markdown代码块的开始和结束位置
    start_marker = "```markdown"
    end_marker = "```"

    start_index = response.find(start_marker)
    end_index = response.find(end_marker, start_index + len(start_marker))

    if start_index != -1 and end_index != -1:
        # 提取markdown代码块内容
        markdown_block = response[start_index + len(start_marker):end_index].strip()
        print(f"Markdown代码块：\n{markdown_block}")
    else:
        markdown_block = "Markdown代码块未找到"

    return markdown_block

markdown_code_block=extract_markdown_block(response_content)

with open('word_table.md', 'w', encoding='utf-8') as f:
    f.write(markdown_code_block)
print("Markdown代码块已写入 word_table.md 文件")
