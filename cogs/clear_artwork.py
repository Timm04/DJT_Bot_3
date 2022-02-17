import asyncio
import discord
from discord.ext import commands
from discord.ext import tasks
from datetime import datetime
from datetime import timedelta
import json


with open(f"cogs/guild_data.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]

class Deleter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guild_id)
        self.clear_channel.start()

    @tasks.loop(minutes=600)
    async def clear_channel(self):
        artwork_channel = discord.utils.get(self.myguild.channels, name="artwork")
        print("Attempting to purge artwork")
        delete_limit = timedelta(hours=12)
        await artwork_channel.purge(limit=1000, before=datetime.utcnow() - delete_limit)
        print("Purged artwork.")

def setup(bot):
    bot.add_cog(Deleter(bot))