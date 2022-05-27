"""Cog for random additional functions and testing."""
import discord
import re
import asyncio
import json
from discord.ext import commands
from datetime import timedelta

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

    @commands.command()
    async def timeout(self, ctx: commands.Context, hours: str):
        """<hours> Mute yourself for a specific amount of hours."""
        if not hours.isnumeric():
            await ctx.send("Please specify the number of hours to mute yourself.")
            return
        if int(hours) > 12:
            await ctx.send("You can only mute yourself for a maximum amount of 12 hours.")
            return
        hours_to_mute = timedelta(hours=int(hours))
        await ctx.author.timeout_for(hours_to_mute)
        await ctx.send(f"{ctx.author.mention} You muted yourself for {int(hours)} hours.")

    @commands.command()
    async def createvc(self, ctx: commands.Context, channel_name):
        """`<channel_name>` Create a custom temporary voice chat channel."""
        if ctx.author.voice:
            other_category = discord.utils.get(ctx.guild.categories, name="OTHER")
            free_talk_position = discord.utils.get(ctx.guild.voice_channels, name="free-talk 256kbps").position
            custom_channel = await ctx.guild.create_voice_channel(channel_name, category=other_category,
                                                                  position=free_talk_position+1)
            await ctx.author.move_to(custom_channel)
            await ctx.send(f"Created custom channel `{custom_channel.name}`. Channel will be deleted when all users left.")

            while custom_channel.members:
                await asyncio.sleep(10)

            await custom_channel.delete(reason="Empty channel.")
            await ctx.send(f"Deleted custom channel `{custom_channel.name}` as all members left.")

        else:
            await ctx.send("You have to join a voice channel to use this command.")
            return




def setup(bot):
    bot.add_cog(Extras(bot))