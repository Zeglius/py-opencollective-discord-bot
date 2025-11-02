import os
import re
from functools import lru_cache

import discord
import requests

ORG_NAME = os.getenv("OPENCOLLECTIVE_ORG_NAME", "bazzite-eu")
GUILD_ID = os.getenv("DISCORD_GUILD_ID", "")


# opencollective_tier : discord_role
# Add items here as we need them
TIER_ROLES_MAP: dict[str, str] = {
    "Root-Access Legend": "root-access-legend",
    "Low-Spec Casual": "low-spec-casual",
}


def get_discord_role_from_oc_tier(tier: str, guild: discord.Guild):
    rol = discord.utils.get(guild.roles, name=TIER_ROLES_MAP.get(tier))
    if not rol:
        raise Exception(
            f"ERROR: Did not find discord role with associated opencollective tier '{tier}'"
        )
    return rol


intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)


@lru_cache(maxsize=128)
def get_backers(org) -> list[dict]:
    members = requests.get(
        f"https://opencollective.com/{org}/members.json?limit=100&offset=0"
    ).json()
    return [
        x
        for x in members
        if x["role"] == "BACKER"
        and x.get("description") is not None
        and x.get("tier") in TIER_ROLES_MAP.keys()
    ]


def parse_discord_username(backer: dict) -> str | None:
    desc = str(backer.get("description"))
    return (
        re.findall(r"discord:?\W*@?(\w+)(?=$|\W)", desc, re.IGNORECASE).pop(0)
        if "discord: " in desc
        else None
    )


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    backers = get_backers(ORG_NAME)
    print(f"Found {len(backers)} elegible members for roles")
    guild = discord.utils.get(client.guilds, id=GUILD_ID)
    if not guild:
        raise Exception("Guild not found")

    for backer in backers:
        role = get_discord_role_from_oc_tier(backer.get("tier", ""), guild=guild)
        if not role:
            continue

        username = parse_discord_username(backer)
        if not username:
            print(
                f"ERROR: no discord username found for backer with id={backer.get('id', '')}. skipping..."
            )
            continue
        member = guild.get_member_named(username)
        if not member:
            print(
                f"ERROR: member with username {username} not found in discord guild. skipping..."
            )
            continue
        try:
            await member.add_roles(role)
        except Exception:
            print(f"ERROR: adding {role} to {member.name}")
        else:
            print(f"Added role {role} to member {username}")
    await client.close()


client.run(os.environ["DISCORD_TOKEN"])
