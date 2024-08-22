from bs4 import BeautifulSoup

import re
import json
from json import JSONDecodeError

from langchain_community.chat_models import ChatZhipuAI
from langchain_core.output_parsers import StrOutputParser, BaseOutputParser
from langchain_core.exceptions import OutputParserException
import dotenv

dotenv.load_dotenv()

glm4 = ChatZhipuAI(model="GLM-4-0520", temperature=0.3, max_tokens=99999999)

CUSTOM_TERMS = {
    "寸草": "InchDance",
    "寸草舞集": "InchDance",
    "作品「蛮好」": "「Most of The Time is Boring」",
    "1933 老场坊": "1933 old Millfun",
    "不止跳舞即兴艺术节": "Beyond Dance Improve Festival",
}


class JsonOutputParser(BaseOutputParser):
    def parse(self, text: str) -> dict:
        json_pattern = r'(\{.*\}|\[.*\])'
        match = re.search(json_pattern, text, re.DOTALL)
        if not match:
            msg = "No JSON content found in text"
            raise OutputParserException(msg, llm_output=text)
        json_content = match.group()
        try:
            return json.loads(json_content)
        except JSONDecodeError as e:
            msg = f"Invalid json output: {text}"
            raise OutputParserException(msg, llm_output=text) from e


str_parser = StrOutputParser()
json_parser = JsonOutputParser()


def translate_html(html_content, target_lang='英语'):
    soup = BeautifulSoup(html_content, 'html.parser')

    # 定义需要翻译的标签
    translate_tags = ['title', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'span', 'div']

    # 用于存储短文本的字典
    short_texts = {}

    # 用于存储长文本的列表
    long_texts = []

    # 遍历所有需要翻译的标签
    for tag in soup.find_all(translate_tags):
        if tag.string and tag.string.strip():
            text = tag.string.strip()
            if len(text) < 50:  # 定义短文本的长度阈值
                short_texts[text] = ""
            else:
                long_texts.append((tag, text))

    # 创建专有名词翻译指南
    terms_guide = "专有名词翻译指南：\n"
    for term, translation in CUSTOM_TERMS.items():
        terms_guide += f"- {term}: {translation}\n"

    # 翻译短文本
    if short_texts:
        prompt = (f"请将以下 json 的 key 翻译成{target_lang}放在 value 里，请只输出 json，不要输出额外内容。\n"
                  f"请遵循以下专有名词翻译指南：\n{terms_guide}\n"
                  f"{json.dumps(short_texts, ensure_ascii=False)}\n\n")
        chain = glm4 | json_parser
        translated_short_texts = chain.invoke(prompt)

        # 替换短文本
        for tag in soup.find_all(translate_tags):
            if tag.string and tag.string.strip() in translated_short_texts:
                tag.string.replace_with(translated_short_texts[tag.string.strip()])

    # 翻译长文本
    for tag, text in long_texts:
        prompt = (f"请将以下文本翻译成{target_lang}，保持原文的格式和标点符号。\n"
                  f"请遵循以下专有名词翻译指南：\n{terms_guide}\n\n{text}\n\n")
        chain = glm4 | str_parser
        translated_text = chain.invoke(prompt)
        tag.string.replace_with(translated_text)

    return str(soup)


def main(cn_file_name, en_file_name):
    with open(cn_file_name) as f:
        html_content = f.read()
    en_html_content = translate_html(html_content)
    with open(en_file_name, "w") as f:
        f.write(en_html_content)


if __name__ == "__main__":
    main("docs/zh/festivals/20240821.find_2017_you.md", "docs/en/festivals/20240821.find_2017_you.md")
