"""Cog for tracking deleted messages temporarily."""

import json
import discord
from discord.ext import commands
from discord.ext import tasks
from datetime import datetime
from datetime import timedelta

#############################################################
# Variables (Temporary)
with open(f"cogs/guild_data.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]
    log_channel_id = data_dict["elite_mod_channel_id"]
    mod_role_id = data_dict["mod_role_id"]
    admin_role_id = data_dict["admin_role_id"]
    mod_channel_id = 862728099790323742

def is_mod_or_admin():
    async def predicate(ctx):
        run_command = False
        for role in ctx.author.roles:
            if role.id == mod_role_id or role.id == admin_role_id:
                run_command = True
        return run_command
    return commands.check(predicate)
#############################################################

class DeletedMSG(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guild_id)
        self.log_channel = self.bot.get_channel(log_channel_id)
        self.delete_limit = timedelta(hours=24)
        self.deleter.start()

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.channel in self.myguild.channels and message.channel is not self.log_channel:
            try:
                await self.log_channel.send(f"User {message.author.mention} (ID: {message.author.id}) deleted in channel {message.channel.mention}:\n"
                                            f"`{message.content}`")
            except discord.errors.HTTPException:
                pass

            try:
                if message.attachments:
                    for attachement in message.attachments:
                        image = await attachement.to_file(use_cached=True)
                        await self.log_channel.send(file=image)

            except AttributeError:
                pass
            except discord.errors.Forbidden:
                await self.log_channel.send("Unable to get file.")
            except discord.errors.NotFound:
                await self.log_channel.send("Unable to get file.")

    @tasks.loop(minutes=100.0)
    async def deleter(self):
        await self.log_channel.purge(before=datetime.utcnow() - self.delete_limit)
        # async for message in self.log_channel.history(limit=None, before=datetime.utcnow() - self.delete_limit):
        #     await message.delete(delay=5)

    @commands.command(hidden=True)
    @is_mod_or_admin()
    async def clear(self, ctx):
        await ctx.send("Clearing channel.")
        async for message in self.log_channel.history(limit=None):
            await message.delete(delay=1)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        admin_role = self.myguild.get_role(admin_role_id)
        mod_channel = self.myguild.get_channel(mod_channel_id)
        await mod_channel.send(f"{admin_role.mention} {user.mention} {user.name} just got banned!")





def setup(bot):
    bot.add_cog(DeletedMSG(bot))