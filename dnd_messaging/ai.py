import abc
import re
from datetime import datetime, timedelta
from pathlib import Path
from random import randrange, choice

import groq
import hikari
import tanjun
import tiktoken
from anthropic import AsyncAnthropic
from atsume.settings import settings
from groq import AsyncGroq

from .tokenizer import Tokenizer as LlamaTokenizer
from .prompts import SCORE_PROMPT, REWRITE_PROMPT, SCORE_REGEX, CHAT_LOG_PROMPT

STATUS_REGEX = re.compile("^-#.*?(?:success!|failure!)\n")


def sanitize_message(message: hikari.Message):
    text = message.content
    for mention in message.user_mentions.values():
        text = text.replace(f"<@{mention.id}>", mention.nickname)
    text = STATUS_REGEX.sub("", text)
    return text


class AIClientError(Exception):
    pass

class AIResponseError(AIClientError):
    pass

class AIServiceUnavailable(AIResponseError):
    pass

class AIClient(abc.ABC):
    @abc.abstractmethod
    def count_tokens(self, text: str) -> int:
        ...

    @abc.abstractmethod
    async def inference(self, messages: list[dict], max_tokens=1000) -> str:
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
        try:
            message = await self.client.chat.completions.create(model=self.model, messages=messages, max_tokens=max_tokens)
        except groq.InternalServerError:
            raise AIServiceUnavailable()
        return message.choices[0].message.content


class AnthropicClient(AIClient):
    def __init__(self):
        # self.tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
        self.anthropic = AsyncAnthropic(api_key=settings.ANTHROPIC_KEY)
        self.model = settings.ANTHROPIC_MODEL

    def count_tokens(self, text: str) -> int:
        return 0

    async def inference(self, messages: list[dict], max_tokens=1000) -> str:
        # Anthropic is a stick in the mud
        system_message = "\n".join([m["content"] for m in messages if m["role"] == "system"])
        fixed_messages = []
        for m in messages:
            if m["role"] == "system":
                continue
            if not fixed_messages:
                fixed_messages.append(m)
                continue
            if m["role"] == fixed_messages[-1]["role"]:
                fixed_messages[-1]["content"] += "\n" + m["content"]
            else:
                fixed_messages.append(m)

        # How annoying can you be?
        if not fixed_messages or fixed_messages[0]["role"] == "assistant":
            fixed_messages.insert(0, {"role": "user", "content": "..."})

        message = await self.anthropic.messages.create(model=self.model, messages=fixed_messages,
                                                       max_tokens=max_tokens, system=system_message)
        return message.content[0].text


ai_client = GroqClient()
anthropic_client = AnthropicClient()

async def message_to_log(client: tanjun.Client, channel: hikari.GuildTextChannel) -> str:
    budget = settings.TOKEN_BUDGET
    messages = []
    log = []
    user_cache = {}
    async for m in channel.fetch_history(before=datetime.now()):
        messages.append(m)
        if len(messages) > 10:
            break
    for m in messages:
        if m.content is None:
            continue

        if m.author not in user_cache:
            if m.author.is_bot and m.author.discriminator == "0000":
                name = m.author.username
            else:
                member = await client.rest.fetch_member(channel.guild_id, m.author)
                user_cache[m.author] = member.display_name
                name = member.display_name
        else:
            name = user_cache[m.author]

        log.insert(0, f"{name}: {sanitize_message(m)}")
        budget -= ai_client.count_tokens(log[0])
        if budget < 0:
            break

    return "\n\n".join(log)


async def score_message(log: str, member: hikari.Member, message: str) -> tuple[str, int] | None:
    prompt = SCORE_PROMPT.format(chat_log=log, message=message, user=member.display_name)

    parsed = None
    for i in range(5):
        try:
            result = await ai_client.inference(messages=[{"role": "system", "content": prompt}])
        except AIResponseError:
            return None
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
    if randrange(0, 2) == 0:
        chat_log = CHAT_LOG_PROMPT.format(chat_log=log)
    else:
        chat_log = ""

    prompt = REWRITE_PROMPT.format(chat_log=chat_log, message=message, category=category, user=member.display_name)

    chosen_client = choice([ai_client, anthropic_client])

    return await chosen_client.inference(messages=[{"role": "system", "content": prompt}])
