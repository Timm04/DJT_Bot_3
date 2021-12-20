"""Ensure accounts are at least a month old before they can post images."""

import discord
from discord.ext import commands
import json
import asyncio
from datetime import datetime

with open(f"cogs/guild_data.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]
    log_channel_id = data_dict["elite_mod_channel_id"]
    mod_role_id = data_dict["mod_role_id"]

class AccountAge(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guild_id)
        self.log_channel = self.bot.get_channel(log_channel_id)
        self.mod_role = self.myguild.get_role(mod_role_id)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id == self.bot.user.id:
            return

        if message.guild:
            time_since_account_creation = datetime.now() - message.author.created_at
            if time_since_account_creation.days < 30 and message.attachments:

                await message.delete()
                await asyncio.sleep(1)

                await self.log_channel.send(f"{self.mod_role.mention} The user `{message.author.name}` with the ID `{message.author.id}` just "
                                            f"tried to post these images. If it's explicit please ban him. (This "
                                            f"message was sent due to the relevant account being younger than 30 days)."
                                            f"\nYou can ban people with their id like this for example:\n"
                                            f"`?ban 520876114093146113 Scat Posting`")

                await asyncio.sleep(1)
                await message.author.create_dm()
                private_channel = message.author.dm_channel
                await asyncio.sleep(1)
                await private_channel.send("Your account has to be at least 30 days old before you can send images.")

def setup(bot):
    bot.add_cog(AccountAge(bot))