"""Cog for random additional functions and testing."""
import discord
import re
import asyncio
import json
from discord.ext import commands
from discord.ext import tasks
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
        self.check_custom_vcs.start()
        await asyncio.sleep(600)
        self.add_members_to_movie.start()

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

    # @commands.command()
    # async def timeout(self, ctx: commands.Context, hours: str):
    #     """<hours> Mute yourself for a specific amount of hours."""
    #     if not hours.isnumeric():
    #         await ctx.send("Please specify the number of hours to mute yourself.")
    #         return
    #     if int(hours) > 12:
    #         await ctx.send("You can only mute yourself for a maximum amount of 12 hours.")
    #         return
    #     hours_to_mute = timedelta(hours=int(hours))
    #     await ctx.author.timeout_for(hours_to_mute)
    #     await ctx.send(f"{ctx.author.mention} You muted yourself for {int(hours)} hours.")

    @commands.command()
    async def createvc(self, ctx: commands.Context, *, channel_name):
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

            await custom_channel.delete(reason="Empty custom channel.")
            await ctx.send(f"Deleted custom channel `{custom_channel.name}` as all members left.")

        else:
            await ctx.send("You have to join a voice channel to use this command.")
            return

    @tasks.loop(minutes=5.0)
    async def check_custom_vcs(self):
        standard_channels = ["free-talk 64kbps", "free-talk 256kbps"]
        self.myguild: discord.Guild
        for voice_channel in self.myguild.voice_channels:
            if voice_channel.name not in standard_channels:
                if not voice_channel.members:
                    vc_chat = discord.utils.get(self.myguild.channels, name="vc-chat")
                    await vc_chat.send(f"Deleted custom channel `{voice_channel.name}` as all members left.")
                    await voice_channel.delete(reason="Empty custom channel.")

    @tasks.loop(minutes=60.0)
    async def add_members_to_movie(self):
        movie_role = discord.utils.get(self.myguild.roles, name="Movie")
        movie_thread = discord.utils.get(self.myguild.threads, name="Movie Watching")
        thread_member_ids = [member.id for member in await movie_thread.fetch_members()]
        added_members = []
        for member in movie_role.members:
            if member.id not in thread_member_ids:
                await asyncio.sleep(1)
                await movie_thread.add_user(member)
                added_members.append(str(member))
                print(f"Added {member.name} to the movie thread.")

        if added_members:
            member_string = ", ".join(added_members)
            await movie_thread.send(f"Added the following members to the thread: {member_string}")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def superpurge(self, ctx: commands.Context):
        await ctx.channel.purge(limit=500)
        await ctx.send("Done.")




def setup(bot):
    bot.add_cog(Extras(bot))