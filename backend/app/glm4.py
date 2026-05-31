import os
import re

from zhipuai import ZhipuAI


# def extend_description(description: str) -> str:
#     client = ZhipuAI(api_key=os.getenv("ZHIPUAI_API_KEY"))
#     myprompt = f'请根据下面这句话“{description}”，给我二到四个现代汉语的短句来描述其中关键意象，用逗号分割，我要用来绘制一副图画。只用给我几个词就好，不要排序，不要任何解释性的、描述性的话或者注释。'
#     response = client.chat.asyncCompletions.create(
#         model="glm-4",  # 使用指定的模型
#         messages=[
#             {
#                 "role": "user",
#                 "content": myprompt
#             }
#         ],
#     )
#
#     # 获取任务ID并初始化变量
#     task_id = response.id
#     task_status = ''
#     get_cnt = 0
#
#     # 检查任务状态，直到完成或失败
#     while task_status != 'SUCCESS' and task_status != 'FAILED' and get_cnt <= 40:
#         result_response = client.chat.asyncCompletions.retrieve_completion_result(id=task_id)
#         task_status = result_response.task_status
#
#         # 检查间隔，避免频繁查询
#         time.sleep(2)
#         get_cnt += 1
#
#     # 任务成功，提取文本
#     if task_status == 'SUCCESS':
#         expanded_text = result_response.choices[0].message.content
#         return expanded_text
#     else:
#         return description  # 如果任务失败，返回原始描述

def extend_description(description: str, n_max_retries: int = 5) -> str:
    verse = description
    api_key = os.getenv("ZHIPUAI_API_KEY")
    if not api_key:
        return verse
    client = ZhipuAI(api_key=api_key)

    get_poem_name_prompt = f"""{verse}
这句诗句来自于哪一首诗歌？
你只需要返回诗歌的名字，不需要返回其它信息。使用书名号包裹诗歌的名字"""

    # 找出诗句来自于哪一首诗
    poem_name = ""
    for _ in range(n_max_retries):
        response_poem_name = client.chat.completions.create(
            model="glm-4-plus",  # 填写需要调用的模型编码
            messages=[
                {"role": "user", "content": get_poem_name_prompt},
            ],
            temperature=0.8,
        )
        poem_name_raw = response_poem_name.choices[0].message.content
        match = re.search(r'《(.*?)》', poem_name_raw)
        if match:
            poem_name = match.group(1)
            break

    # 给出诗句的解析
    if poem_name:
        get_poem_description_prompt = f"""使用简单易懂的语言，给出《{poem_name}》中，“{verse}”这句诗句的解析"""
    else:
        get_poem_description_prompt = f"""使用简单易懂的语言，给出“{verse}”这句诗句的解析"""

    response_poem_description = client.chat.completions.create(
        model="glm-4-plus",  # 填写需要调用的模型编码
        messages=[
            {"role": "user", "content": get_poem_description_prompt},
        ],
        temperature=0.8,
    )
    poem_description = response_poem_description.choices[0].message.content.replace("\n\n", "\n")
    

    # 使用直白的语言重写诗句
    get_plain_description = f"""根据诗句解析，将“{verse}”这句诗句重写为一段直白的文字。

### 规则：
1. 重写后的诗句需要保留诗句中明确的意象。
2. 重写时只需要保留事实，使用的语法要足够简单易懂，并删除所有的比喻。
3. 不要出现任何人称代词，比如“你”、“我”、“他”、“她们”等。
4. 重写后的文本不需要遵守诗歌的结构与韵律，重写后的文本不需要考虑文学上的美感。

你只需要返回重写后的文本，不要对你写的文本进行解析。
确保你的回答只有一行，不包含任何换行符。

### 对“{verse}”的解析如下：
{poem_description}

重写后的文本："""
    plain_description = ""
    for _ in range(n_max_retries):
        response_plain_description = client.chat.completions.create(
            model="glm-4-plus",  # 填写需要调用的模型编码
            messages=[
                {"role": "user", "content": get_plain_description},
            ],
            temperature=0.8,
        )
        plain_description = response_plain_description.choices[0].message.content
        if len(plain_description.split("\n")) == 1:
            break
        else:
            plain_description = ""

    return plain_description if plain_description else verse

# def extend_description(description: str, n_max_retries: int = 5) -> str:
#     verse = description
#     client = ZhipuAI(api_key=os.getenv("ZHIPUAI_API_KEY"))
#
#     get_poem_name_prompt = f"""{verse}
# 这句诗句来自于哪一首诗歌？
# 你只需要返回诗歌的名字，不需要返回其它信息。使用书名号包裹诗歌的名字"""
#
#     # 找出诗句来自于哪一首诗
#     poem_name = ""
#     for _ in range(n_max_retries):
#         response_poem_name = client.chat.completions.create(
#             model="glm-4",  # 填写需要调用的模型编码
#             messages=[
#                 {"role": "user", "content": get_poem_name_prompt},
#             ],
#             temperature=0.0,
#         )
#         poem_name_raw = response_poem_name.choices[0].message.content
#         match = re.search(r'《(.*?)》', poem_name_raw)
#         if match:
#             poem_name = match.group(1)
#             break
#
#     # 给出诗句的解析
#     if poem_name:
#         get_poem_description_prompt = f"""使用简单易懂的语言，给出《{poem_name}》中，“{verse}”这句诗句的解析"""
#     else:
#         get_poem_description_prompt = f"""使用简单易懂的语言，给出“{verse}”这句诗句的解析"""
#
#     response_poem_description = client.chat.completions.create(
#         model="glm-4",  # 填写需要调用的模型编码
#         messages=[
#             {"role": "user", "content": get_poem_description_prompt},
#         ],
#         temperature=0.0,
#     )
#     poem_description = response_poem_description.choices[0].message.content.replace("\n\n", "\n")
#
#     # 使用直白的语言重写诗句
#     get_plain_description = f"""根据诗句解析，将“{verse}”这句诗句重写为一段直白的文字。
#
# ### 规则：
# 1. 重写后的诗句需要保留诗句中明确的意象。
# 2. 重写时只需要保留事实，使用的语法要足够简单易懂，并删除所有的比喻。
# 3. 不要出现任何人称代词，比如“你”、“我”、“他”、“她们”等。
# 4. 重写后的文本不需要遵守诗歌的结构与韵律，重写后的文本不需要考虑文学上的美感。
#
# 你只需要返回重写后的文本，不要对你写的文本进行解析。
# 确保你的回答只有一行，不包含任何换行符。
#
# ### 对“{verse}”的解析如下：
# {poem_description}
#
# 重写后的文本："""
#     plain_description = ""
#     for _ in range(n_max_retries):
#         response_plain_description = client.chat.completions.create(
#             model="glm-4",  # 填写需要调用的模型编码
#             messages=[
#                 {"role": "user", "content": get_plain_description},
#             ],
#             temperature=0.0,
#         )
#         plain_description = response_plain_description.choices[0].message.content
#         if len(plain_description.split("\n")) == 1:
#             break
#         else:
#             plain_description = ""
#     if not plain_description:
#         return verse
#
#     # 对描述再次进行总结
#     get_landscape_prompt = f"""### 文本：
# {plain_description}
#
# 将文本按照指定的规则，总结为数个短语，使用逗号分割。
#
# ### 规则：
# 1. 提取出文本中的事实。
# 2. 删去所有修饰性的词语，比如“什么像什么”等。
#
# 你只需要返回短语，不需要返回任何解释。
# 确保你的回答只有一行，不包含任何换行符。
#
# 总结："""
#     landscape = ""
#     for _ in range(n_max_retries):
#         response_landscape = client.chat.completions.create(
#             model="glm-4",  # 填写需要调用的模型编码
#             messages=[
#                 {"role": "user", "content": get_landscape_prompt},
#             ],
#             temperature=0.0,
#         )
#         landscape = response_landscape.choices[0].message.content
#         if len(landscape.split("\n")) == 1:
#             break
#         else:
#             landscape = ""
#     return landscape if landscape else plain_description
