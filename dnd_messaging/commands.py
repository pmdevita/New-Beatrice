import alluka
import hikari
import tanjun
import atsume

from typing import Optional, cast


from .ai import score_message, rewrite_failed_message, message_to_log
from .models import *


@tanjun.as_message_command("dnd_stats")
async def set_dnd_stats(ctx: tanjun.abc.Context):
    channel, created = await DNDStatsChannel.objects.get_or_create(guild=ctx.guild_id,
                                                                   _defaults={"channel": ctx.channel_id})
    channel.channel = ctx.channel_id
    await channel.update()
    channel = await ctx.fetch_channel()
    await ctx.respond(f"Set DND stats channel to {channel.mention}.")


async def generate_member_stats(client: tanjun.Client, guild_id: hikari.Snowflake, member: hikari.Member) -> Optional[
    DNDStats]:
    channel = await DNDStatsChannel.objects.filter(guild=guild_id).first_or_none()
    if not channel:
        return None

    stats, created = await DNDStats.objects.get_or_create(user=member.id, _defaults={
        "charisma": roll_stat(),
        "intelligence": roll_stat(),
        "wisdom": roll_stat(),
        "deception": roll_stat(),
        "humor": roll_stat()
    })

    if created:
        c = cast(hikari.TextableChannel, await client.rest.fetch_channel(channel.channel))
        await c.send(f"""DND stats for {member.mention}
- Charisma: {stats.charisma} ({ability_score_to_modifier(stats.charisma)})
- Intelligence: {stats.intelligence} ({ability_score_to_modifier(stats.intelligence)})
- Wisdom: {stats.wisdom} ({ability_score_to_modifier(stats.wisdom)})
- Deception: {stats.deception} ({ability_score_to_modifier(stats.deception)})
- Humor: {stats.humor} ({ability_score_to_modifier(stats.humor)})
""")

    return stats


abbreviations = {
    "Charisma": "CHR",
    "Intelligence": "INT",
    "Wisdom": "WIS",
    "Deception": "DEC",
    "Humor": "HUM"
}


@atsume.with_listener
async def on_message(event: hikari.events.MessageCreateEvent, client: alluka.Injected[tanjun.Client]):
    message = event.message.content
    if message is None:
        return

    # Stop from trying to correct messages it shouldn't
    if message[:3] in ("-b ", "-t "):
        return

    if event.author.is_bot:
        bot = await client.rest.fetch_my_user()
        if event.author.id != bot.id:
            return
        elif "DND stats for" in message:
            return

    stats = await generate_member_stats(client, event.message.guild_id, event.message.member)
    if stats is None:
        return

    member = await client.rest.fetch_member(event.message.guild_id, event.message.author)
    channel = cast(hikari.GuildTextChannel, await event.message.fetch_channel())
    embeds = event.message.embeds
    attachments = event.message.attachments

    if not attachments:
        await event.message.delete()

    async with channel.trigger_typing():
        log = await message_to_log(client, channel)
        result = await score_message(log, member, message)
        if result is None:
            new_message = message
        else:
            category, score = result
            abbr_cat = abbreviations[category]

            user_ability_score = getattr(stats, category.lower())
            user_stat = ability_score_to_modifier(user_ability_score)
            dice_roll = randrange(1, 21)

            if user_stat + dice_roll < score or dice_roll == 1:
                new_message = await rewrite_failed_message(log, member, message, category)

                new_message = f"-# {abbr_cat} {score} - rolled a {dice_roll} - failure!\n{new_message}"
            else:
                new_message = f"-# {abbr_cat} {score} - rolled a {dice_roll} - success!\n{message}"

        await fake_message(client, channel, member, new_message, embeds, attachments)
        if attachments:
            await event.message.delete()


async def fake_message(client: tanjun.Client, channel: hikari.GuildTextChannel, user: hikari.Member, message: str, embeds, attachments):
    webhooks = await client.rest.fetch_channel_webhooks(channel)
    if len(webhooks) == 0:
        webhook = await client.rest.create_webhook(channel, "DND Messaging")
    else:
        webhook = webhooks[0]
    await webhook.execute(message, username=user.display_name, avatar_url=user.avatar_url)
