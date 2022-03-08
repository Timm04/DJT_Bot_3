import asyncio
import discord
from discord.ext import commands
from discord.ext import tasks
from datetime import datetime
from datetime import timedelta
import json
from better_profanity import profanity
import boto3


with open(f"cogs/guild_data.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]

class Deleter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.s3_client = boto3.client('s3')
        self.fname = "gamerleaderboard.json"

        custom_badwords = ['tranny', 'trannies']
        profanity.add_censor_words(custom_badwords)

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

    def pull_all_records(self):
        self.s3_client.download_file('djtbot', self.fname, f'data/{self.fname}')
        with open(f"data/{self.fname}") as json_file:
            manga_dict = json.load(json_file)
        return manga_dict

    def push_all_records(self, data_dict):
        with open(f'data/{self.fname}', 'w') as json_file:
            json.dump(data_dict, json_file)
        self.s3_client.upload_file(f'data/{self.fname}', "djtbot", f'{self.fname}')

    async def update_gamer_leaderboard(self, point_additions=None):
        point_dictionary = self.pull_all_records()

        if point_additions:
            for user_id, additional_points in point_additions.items():
                point_dictionary[str(user_id)] = point_dictionary.get(str(user_id), 0) + additional_points

        self.push_all_records(point_dictionary)

        otaku_channel = discord.utils.get(self.myguild.channels, name="otaku")
        otaku_pins = await otaku_channel.pins()
        old_pins = []
        for message in otaku_pins:
            if message.author.id == self.bot.user.id and message.content.startswith("Gamer"):
                old_pins.append(message)

        message_string = ["Gamer Leaderboard:"]
        edit_index = 0
        new_pins = []
        sorted_users = sorted(point_dictionary, key=point_dictionary.get, reverse=True)
        for index, current_userid in enumerate(sorted_users):
            position = index + 1
            userline = f"{position}. <@!{int(current_userid)}> : {point_dictionary[current_userid]}点."
            message_string.append(userline)
            if len("\n".join(message_string)) > 1800:
                try:
                    await old_pins[edit_index].edit(content="\n".join(message_string))
                except IndexError:
                    new_pins.append(await otaku_channel.send("\n".join(message_string)))
                edit_index += 1
                message_string = []

        if message_string:
            try:
                await old_pins[edit_index].edit(content="\n".join(message_string))
            except IndexError:
                new_pins.append(await otaku_channel.send("\n".join(message_string)))

        if new_pins:
            for message in new_pins[::-1]:
                await message.pin()

    @tasks.loop(minutes=30)
    async def clear_curse_words_loop(self):

        delete_limit = timedelta(hours=24)

        def contains_curse_words(message: discord.Message):
            if message.author.bot:
                return False
            elif "nigger" in message.content.lower():
                return True
            elif "tranny" in message.content.lower():
                return True
            else:
                return profanity.contains_profanity(message.content)

        for channel in self.myguild.channels:
            if isinstance(channel, discord.TextChannel):
                print(f"Attempting to purge {channel.name}")
                await asyncio.sleep(5)
                purged_messages = await channel.purge(limit=1000, check=contains_curse_words,
                                                      before=datetime.utcnow() - delete_limit)
                if len(purged_messages) > 0:
                    # await channel.send(f"Deleted {len(purged_messages)} gamer messages.")
                    delete_string = "\n".join([message.content for message in purged_messages])
                    print(f"Deleted {len(purged_messages)} gamer messages with the following content:\n{delete_string}")

                    point_additions = dict()
                    for message in purged_messages:
                        point_additions[message.author.id] = point_additions.get(message.author.id, 0) + 1

                    await self.update_gamer_leaderboard(point_additions)


        for thread in self.myguild.threads:
            print(f"Attempting to purge {thread.name}")
            await asyncio.sleep(5)
            purged_messages = await thread.purge(limit=500, check=contains_curse_words,
                                                  before=datetime.utcnow() - delete_limit)
            if len(purged_messages) > 0:
                # await thread.send(f"Deleted {len(purged_messages)} gamer messages.")
                delete_string = "\n".join([message.content for message in purged_messages])
                print(f"Deleted {len(purged_messages)} gamer messages with the following content:\n{delete_string}")

                point_additions = dict()
                for message in purged_messages:
                    point_additions[message.author.id] = point_additions.get(message.author.id, 0) + 1

                await self.update_gamer_leaderboard(point_additions)

def setup(bot):
    bot.add_cog(Deleter(bot))