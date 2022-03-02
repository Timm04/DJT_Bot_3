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
        await asyncio.sleep(30)
        self.clear_curse_words_loop.start()

    @tasks.loop(minutes=300)
    async def clear_channel(self):
        artwork_channel = discord.utils.get(self.myguild.channels, name="artwork")
        print("Attempting to purge artwork")
        delete_limit = timedelta(hours=12)
        await artwork_channel.purge(limit=1000, before=datetime.utcnow() - delete_limit)
        print("Purged artwork.")

    @tasks.loop(minutes=30)
    async def clear_curse_words_loop(self):
        delete_limit = timedelta(hours=6)

        def contains_curse_words(message: discord.Message):
            if "nigger" in message.content.lower():
                return True
            elif "tranny" in message.content.lower():
                return True
            else:
                return False

        for channel in self.myguild.channels:
            if isinstance(channel, discord.TextChannel):
                print(f"Attempting to purge {channel.name}")
                await asyncio.sleep(5)
                purged_messages = await channel.purge(limit=1000, check=contains_curse_words,
                                                      before=datetime.utcnow() - delete_limit)
                if len(purged_messages) > 0:
                    pass
                    # await channel.send(f"Deleted {len(purged_messages)} gamer messages.")

        for thread in self.myguild.threads:
            print(f"Attempting to purge {thread.name}")
            await asyncio.sleep(5)
            purged_messages = await thread.purge(limit=500, check=contains_curse_words,
                                                  before=datetime.utcnow() - delete_limit)
            if len(purged_messages) > 0:
                pass
                # await thread.send(f"Deleted {len(purged_messages)} gamer messages.")

def setup(bot):
    bot.add_cog(Deleter(bot))