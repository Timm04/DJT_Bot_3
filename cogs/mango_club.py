"""
Cog for the manga club.
Displays a leaderboard and allows users to log
number of volumes read in a month.
Most code in this cog is by Anacreon.
"""
from discord.ext import commands
from discord.ext import tasks
import boto3
import json
from datetime import datetime


with open("cogs/guild_data.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]
    manga_channel_id = data_dict['manga_channel_id']

class MangaClub(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.fname = "mangadata.json"
        self.first_iteration = True
        self.s3_client = boto3.client('s3')

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guild_id)
        self.manga_channel = self.bot.get_channel(manga_channel_id)
        self.display_leaderboard.start()

    def pull_all_records(self):
        self.s3_client.download_file('djtbot', self.fname, f'data/{self.fname}')
        with open(f"data/{self.fname}") as json_file:
            manga_dict = json.load(json_file)
        return manga_dict

    def push_all_records(self, manga_dict):
        with open(f'data/{self.fname}', 'w') as json_file:
            json.dump(manga_dict, json_file)
        self.s3_client.upload_file(f'data/{self.fname}', "djtbot", f'{self.fname}')

    @tasks.loop(hours=24)
    async def display_leaderboard(self):
        """
        Send messages to the manga channel showing the entire leaderboard every 24 hours.
        """
        if self.first_iteration:
            self.first_iteration = False
            return
        # unpin old bot messages
        pins = await self.manga_channel.pins()
        for old_pin in pins:
            if old_pin.author.id == self.bot.user.id:
                await old_pin.unpin()

        # send new leaderboard and pin it
        manga_dict = self.pull_all_records()
        new_pins = []
        msg = ''
        for rank, (user_id, record) in enumerate(sorted(manga_dict.items(), key=lambda x: x[1]['score'], reverse=True)):
            msg += f'{rank+1}. <@!{user_id}> : {record["score"]} volumes read\n'
            if len(msg) > 1800:
                new_pins.append(await self.manga_channel.send(msg))
                msg = ''
        if msg:
            new_pins.append(await self.manga_channel.send(msg))
        for m in new_pins[::-1]:
            await m.pin()

    def set_monthly_volumes(self, user_record, vol_count):
        last_update = datetime.fromtimestamp(user_record['last_update']['time'])
        now = datetime.utcnow()

        if last_update.month == now.month:
            user_record['score'] -= user_record['last_update']['count']
        user_record['score'] += vol_count
        user_record['last_update'] = {
            'time': now.timestamp(),
            'count': vol_count
        }

    @commands.command()
    async def mangavols(self, ctx, volume_count):
        """
        <count> Set manga volume count.
        """
        if ctx.channel.id != manga_channel_id:
            return

        user = ctx.author
        volume_count = int(volume_count)
        if 0 < volume_count <= 10:
            manga_dict = self.pull_all_records()
            if user.id not in manga_dict:
                manga_dict[user.id] = {'score': 0, 'last_update': {'time': 0, 'count': 0}}

            self.set_monthly_volumes(manga_dict[user.id], volume_count)
            self.push_all_records(manga_dict)
            await ctx.send(f"Your volumes read for this month is now set to {volume_count}")
        else:
            await ctx.send("Number of volumes must be less than 10.")


def setup(bot):
    bot.add_cog(MangaClub(bot))
