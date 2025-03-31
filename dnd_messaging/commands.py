import alluka
import hikari
import tanjun
import atsume

from typing import Annotated, Optional, cast
from tanjun.annotations import Member, Positional

from .models import *

# Create your commands here.


@tanjun.as_message_command("dnd_message", "hello", "hey", "howdy")
async def dnd_message(
    ctx: tanjun.abc.Context,
) -> None:
    stats = await DNDStats.objects.get_or_create(user=ctx.member.id, _defaults={
        "charisma": roll_stat(),
        "intelligence": roll_stat(),
        "wisdom": roll_stat(),
        "deception": roll_stat(),
        "humor": roll_stat()
    })
    print(stats)
    await ctx.respond(f"hello {stats}")


@tanjun.as_message_command("dnd_stats")
async def set_dnd_stats(ctx: tanjun.abc.Context):
    channel, created = await DNDStatsChannel.objects.get_or_create(guild=ctx.guild_id, _defaults={"channel": ctx.channel_id})
    channel.channel = ctx.channel_id
    await channel.update()
    channel = await ctx.fetch_channel()
    await ctx.respond(f"Set DND stats channel to {channel.mention}.")


async def generate_member_stats(client: tanjun.Client, guild_id: hikari.Snowflake, member: hikari.Member) -> Optional[DNDStats]:
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
- Charisma: {stats.charisma}
- Intelligence: {stats.intelligence}
- Wisdom: {stats.wisdom}
- Deception: {stats.deception}
- Humor: {stats.humor}
""")

    return stats

@atsume.with_listener
async def on_message(event: hikari.events.MessageCreateEvent, client: alluka.Injected[tanjun.Client]):
    original = event.message.content

    # Stop from trying to correct messages it shouldn't
    if original[:3] in ("-b ", "-t "):
        return

    if event.author.is_bot:
        return

    stats = await generate_member_stats(client, event.message.guild_id, event.message.member)



