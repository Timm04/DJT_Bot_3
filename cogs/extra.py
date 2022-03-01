"""Cog for random additional functions and testing."""
import discord
import re
import asyncio
import json
from discord.ext import commands

#############################################################
# Variables (Temporary)
with open(f"cogs/guild_data.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]
    admin_user_id = data_dict["kaigen_user_id"]
#############################################################

class Extras(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guild_id)

    # Send messages over bot
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id == admin_user_id and message.channel == message.author.dm_channel:
            try:
                mychannelid = int(re.findall(r"(^\d+) ", message.content)[0])
                mymessage = re.findall(r"\d+ (.*)", message.content)[0]
            except IndexError:
                return

            print(f"Channel id: {mychannelid}")
            print(f"My message: {mymessage}")

            chatchannel = self.myguild.get_channel(mychannelid)
            await chatchannel.send(mymessage)

    @commands.command()
    async def github(self, ctx):
        """Get a link to the github repository hosting the code for this bot."""
        link = "https://github.com/friedrich-de/DJT_Bot_3"
        await ctx.send(link)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def editmsg(self, ctx, channelid, msgid, content):
        editchannel = self.myguild.get_channel(int(channelid))
        msg = await editchannel.fetch_message(int(msgid))
        await msg.edit(content=content)
        await ctx.send("Success.")

def setup(bot):
    bot.add_cog(Extras(bot))