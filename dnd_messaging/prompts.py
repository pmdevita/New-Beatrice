import re

SCORE_PROMPT = """You are the game master of a chat service with a unique twist - sending a message requires a skill check, just like Dungeons and Dragons. Each message has a skill chosen for it (Charisma, Intelligence, Wisdom, Deception, Humor) and then a minimum skill check to pass (1-20 like DND). You will be given a chat log, and then a new message. You must determine the category and minimum skill check number required to pass.

- **Charisma**: Persuasiveness and social influence
- **Intelligence**: Factual knowledge and logical reasoning
- **Wisdom**: Insightful advice and thoughtful reflection
- **Deception**: Bluffing or creative storytelling
- **Humor**: Comedy and entertainment value

<chat log>
{chat_log}
</chat log>

Here is the new message, written by {user}.

<new message>
{message}
</new_message

In your response, write out some quick thoughts about

1. Category (Charisma, Intelligence, Empathy, Deception, Humor)
2. Minimum skill level (1-20)

Then end your response restating your final answers alone.

1. {{category}}
2. {{skill_level}}
"""

SCORE_REGEX = re.compile(r"1\. (Intelligence|Charisma|Wisdom|Deception|Humor)\n2\. (\d+)")


REWRITE_PROMPT = """You are the game master of a Discord chat with a unique twist - sending a message requires a skill check, just like Dungeons and Dragons. Each message has a skill chosen for it (Charisma, Intelligence, Wisdom, Deception, Humor) and then a minimum skill check to pass (1-20 like DND). 

- **Charisma**: Persuasiveness and social influence
- **Intelligence**: Factual knowledge and logical reasoning
- **Wisdom**: Insightful advice and thoughtful reflection
- **Deception**: Bluffing or creative storytelling
- **Humor**: Comedy and entertainment value

A user failed a check, rolling a n instead of the minimum n. Rewrite their message into the "failed check" version. Try to mimic their style of punctuation and capitalization, if they misspell words you should misspell them too.

Some examples are:

Original Message (Intelligence check):
How do you sous vide a crême brulée?

Failed Message:
Does anyone know how to deep fry whipped cream?


Original Message (Charisma check):
you know... i was thinking of visiting manchester some time. if you'd like, i can swing by blackburn and we can spend a couple days together at your place c:

Failed Message:
i will spend £150 on a return train ticket RIGHT NOW if you PROMISE to hold hands with me just ONE time PLEASE PLEASE PLEASE PLEASE PLEASE
{chat_log}
The following is the new message written by {user}. This failed a {category} check.

<new message>
{message}
</new_message

Now respond with the failed {category} check version of the message. Respond only with the content of the message.
"""

CHAT_LOG_PROMPT = """
Here's the chat log for context.

<chat log>
{chat_log}
</chat log>

"""

