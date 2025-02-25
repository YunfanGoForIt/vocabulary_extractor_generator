import os
import base64
import time
from openai import OpenAI
from pathlib import Path
import re
import csv
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading

def rename_images_in_folder(folder_path, api_key, progress_callback):
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.moonshot.cn/v1",
    )

    files = os.listdir(folder_path)
    image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
    image_files.sort()
    seen_words = set()
    total_images = len(image_files)

    for i, filename in enumerate(image_files, start=1):
        old_file = os.path.join(folder_path, filename)
        file_extension = os.path.splitext(filename)[1]
        new_file = os.path.join(folder_path, f"{i}{file_extension}")
        os.rename(old_file, new_file)
        print(f"Renamed: {old_file} to {new_file}")

        with open(new_file, 'rb') as f:
            img_base = base64.b64encode(f.read()).decode('utf-8')

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

        response_content = response.choices[0].message.content
        print(response_content)
        print(context)

        new_words = response_content.split(', ')
        seen_words.update(new_words)

        # 更新进度条
        progress_callback((i / total_images) * 40)  # 40% for this step

        time.sleep(3)

    with open('all_words.txt', 'w') as f:
        f.write(', '.join(seen_words))
    print(seen_words)
    return seen_words

def generate_word_table(api_key, folder_path, progress_callback):
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.moonshot.cn/v1",
    )
    words = rename_images_in_folder(folder_path, api_key, progress_callback)

    with open('all_words.txt', 'r') as f:
        words_content = f.read()

    words_list = words_content.split(', ')
    sorted_words_list = sorted(words_list)

    with open('all_words.txt', 'w') as f:
        f.write(', '.join(sorted_words_list))

    print("Words have been sorted and written back to all_words.txt")

    file_object = client.files.create(file=Path("all_words.txt"), purpose="file-extract")
    file_content = client.files.content(file_id=file_object.id).text

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

    response_2 = client.chat.completions.create(
        model="moonshot-v1-32k",
        messages=messages,
        temperature=0.3,
        max_tokens=11800,
    )

    response_content = response_2.choices[0].message.content
    markdown_code_block = extract_markdown_block(response_content)

    with open('word_table.md', 'w', encoding='utf-8') as f:
        f.write(markdown_code_block)
    print("Markdown代码块已写入 word_table.md 文件")

    # 更新进度条
    progress_callback(100)  # 100% for this step

def extract_markdown_block(response):
    # 查找markdown代码块的开始和结束位置
    start_marker = "```markdown"
    end_marker = "```"

    start_index = response.find(start_marker)
    end_index = response.find(end_marker, start_index + len(start_marker))

    if start_index != -1 and end_index != -1:
        markdown_block = response[start_index + len(start_marker):end_index].strip()
    else:
        markdown_block = "Markdown代码块未找到"

    return markdown_block

def on_generate():
    api_key = api_key_entry.get()
    folder_path = folder_path_entry.get()

    if not api_key or not folder_path:
        messagebox.showwarning("输入错误", "请确保填写了API Key和选择了文件夹路径。")
        return

    progress['value'] = 0
    root.update_idletasks()

    def worker():
        try:
            generate_word_table(api_key, folder_path, update_progress)
            messagebox.showinfo("完成", "单词表已生成并保存到 word_table.md 文件。")
        except Exception as e:
            messagebox.showerror("错误", f"生成单词表时出错: {str(e)}")

    threading.Thread(target=worker).start()

def update_progress(value):
    progress['value'] = value
    root.update_idletasks()

def select_folder():
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        folder_path_entry.delete(0, tk.END)
        folder_path_entry.insert(0, folder_selected)

root = tk.Tk()
root.title("单词表生成器")

tk.Label(root, text="API Key:").grid(row=0, column=0, padx=10, pady=10)
api_key_entry = tk.Entry(root, width=50)
api_key_entry.grid(row=0, column=1, padx=10, pady=10)

tk.Label(root, text="图片文件夹路径:").grid(row=1, column=0, padx=10, pady=10)
folder_path_entry = tk.Entry(root, width=50)
folder_path_entry.grid(row=1, column=1, padx=10, pady=10)
tk.Button(root, text="选择文件夹", command=select_folder).grid(row=1, column=2, padx=10, pady=10)

tk.Button(root, text="生成", command=on_generate).grid(row=2, column=1, padx=10, pady=10)

progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
progress.grid(row=3, column=0, columnspan=3, padx=10, pady=10)

root.mainloop()
