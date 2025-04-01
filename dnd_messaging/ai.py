import abc
import re
from datetime import datetime, timedelta
from pathlib import Path

import hikari
import tanjun
from atsume.settings import settings
from groq import AsyncGroq

from .tokenizer import Tokenizer as LlamaTokenizer
from .prompts import SCORE_PROMPT, REWRITE_PROMPT, SCORE_REGEX

STATUS_REGEX = re.compile("^-#.*?(?:success!|failure!)\n")


def sanitize_message(message: hikari.Message):
    text = message.content
    for mention in message.user_mentions.values():
        text = text.replace(f"<@{mention.id}>", mention.nickname)
    text = STATUS_REGEX.sub("", text)
    return text


class AIClient(abc.ABC):
    @abc.abstractmethod
    def count_tokens(self, text: str) -> int:
        ...

    @abc.abstractmethod
    async def inference(self, messages: list[dict]) -> str:
        ...


class GroqClient(AIClient):
    def __init__(self):
        path = Path(__file__).parent / "tokenizer.model"
        self.tokenizer = LlamaTokenizer(str(path))
        self.client = AsyncGroq(api_key=settings.GROQ_KEY)
        self.model = settings.GROQ_MODEL

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text, bos=False, eos=False))

    async def inference(self, messages: list[dict], max_tokens=1000) -> str:
        message = await self.client.chat.completions.create(model=self.model, messages=messages, max_tokens=max_tokens)
        return message.choices[0].message.content


ai_client = GroqClient()


async def message_to_log(client: tanjun.Client, channel: hikari.GuildTextChannel) -> str:
    budget = settings.TOKEN_BUDGET
    messages = []
    log = []
    user_cache = {}
    async for m in channel.fetch_history(after=datetime.now() - timedelta(days=1)):
        messages.append(m)
    for m in reversed(messages):
        if m.author not in user_cache:
            if m.author.is_bot and m.author.discriminator == "0000":
                user_cache[m.author] = m.author.username
            else:
                member = await client.rest.fetch_member(channel.guild_id, m.author)
                user_cache[m.author] = member.nickname
        log.insert(0, f"{user_cache[m.author]}: {sanitize_message(m)}")
        budget -= ai_client.count_tokens(log[0])
        if budget < 0:
            break

    return "\n\n".join(log)


async def score_message(log: str, member: hikari.Member, message: str) -> tuple[str, int] | None:
    prompt = SCORE_PROMPT.format(chat_log=log, message=message, user=member.display_name)

    print(prompt)
    print(ai_client.count_tokens(prompt))

    parsed = None
    for i in range(5):
        result = await ai_client.inference(messages=[{"role": "system", "content": prompt}])
        print(result)
        parsed = SCORE_REGEX.findall(result)
        if parsed:
            break

    if parsed is None:
        return None

    if len(parsed) > 1:
        print("uh oh", parsed)

    category = parsed[-1][0]
    try:
        score = int(parsed[-1][1])
    except ValueError:
        return None

    return category, score


async def rewrite_failed_message(log: str, member: hikari.Member, message: str, category: str) -> str:
    prompt = REWRITE_PROMPT.format(chat_log=log, message=message, category=category, user=member.display_name)
    return await ai_client.inference(messages=[{"role": "system", "content": prompt}])
