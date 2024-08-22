import re
import json
import os
from json import JSONDecodeError

from bs4 import BeautifulSoup, NavigableString, Tag

from langchain_community.chat_models import ChatZhipuAI
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser, BaseOutputParser
from langchain_core.exceptions import OutputParserException
import dotenv

dotenv.load_dotenv()

API_KEY = os.getenv('OPENAI_API_KEY')
API_BASE = os.getenv('OPENAI_API_BASE')

glm4 = ChatZhipuAI(model="GLM-4", temperature=0.3)
gpt4o = ChatOpenAI(api_key=API_KEY, base_url=API_BASE, model="gpt-4o", temperature=0.7)
gpt4o_mini = ChatOpenAI(api_key=API_KEY, base_url=API_BASE, model="gpt-4o-mini", temperature=0.7)

llm = gpt4o

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
    translate_tags = ['title', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'span', 'div', 'strong', 'a']

    texts_to_translate = {}

    def process_tag(tag):
        if tag.name in translate_tags:
            if tag.string and tag.string.strip():
                text = tag.string.strip()
                if len(text) <= 1000:
                    texts_to_translate[text] = ""
            else:
                for child in tag.children:
                    if isinstance(child, NavigableString) and child.strip():
                        text = child.strip()
                        if len(text) <= 1000:
                            texts_to_translate[text] = ""
                    elif isinstance(child, Tag):
                        process_tag(child)

    for tag in soup.find_all(translate_tags):
        process_tag(tag)

    terms_guide = "专有名词翻译指南：\n"
    for term, translation in CUSTOM_TERMS.items():
        terms_guide += f"- {term}: {translation}\n"

    translated_texts = {}
    for i in range(0, len(texts_to_translate), 30):
        batch = dict(list(texts_to_translate.items())[i:i + 30])
        prompt = (f"请将以下 json 的 key 翻译成{target_lang}放在 value 里，请只输出 json，不要输出额外内容。\n"
                  f"请遵循以下专有名词翻译指南：\n{terms_guide}\n"
                  f"{json.dumps(batch, ensure_ascii=False)}\n\n")
        chain = llm | json_parser
        try:
            batch_translated = chain.invoke(prompt)
            translated_texts.update(batch_translated)
        except Exception as e:
            print(f"Translation error for batch {i // 30 + 1}: {e}")

    for tag in soup.find_all(translate_tags):
        if tag.string and tag.string.strip() in translated_texts:
            tag.string.replace_with(translated_texts[tag.string.strip()])
        else:
            for child in tag.children:
                if isinstance(child, NavigableString) and child.strip() in translated_texts:
                    new_string = translated_texts[child.strip()]
                    child.replace_with(new_string)

    return str(soup)


def main(cn_file_name):
    en_file_name = cn_file_name.replace("/zh/", "/en/")
    with open(cn_file_name) as f:
        html_content = f.read()
    en_html_content = translate_html(html_content)
    with open(en_file_name, "w") as f:
        f.write(en_html_content)


if __name__ == "__main__":
    main("docs/zh/articles/20240821.zoe_talk_review.md")
