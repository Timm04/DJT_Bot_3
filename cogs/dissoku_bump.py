"""Cog for Dissoku bumping."""

import re
import json
import boto3
import asyncio
import pickle
import discord
from discord.ext import commands
from discord.ext import tasks
from datetime import datetime
from datetime import timedelta

#############################################################
# Variables (Temporary)
# https://pastebin.com/sKYwGbav Dissoku message.
with open(f"cogs/guild_data.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]
    bump_channel_id = data_dict["bump_channel_id"]
    bumper_role = data_dict["bumper_role_id"]
#############################################################

class DissokuBumpCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.waiterindex = 0
        self.starterindex = 0
        self.bumperindex = 0
        self.idleindex = 0
        self.time_idled = 0
        self.s3_client = boto3.client('s3')

    @commands.Cog.listener()
    async def on_ready(self):
        self.minutes_until_next_bump = await self.loadtime()
        self.msg_channel = self.bot.get_channel(bump_channel_id)
        self.myguild = self.bot.get_guild(guild_id)
        self.bumprole = self.myguild.get_role(bumper_role)
        self.startwaiter.start()

    async def savetime(self, minutes_bump=61):
        time_change = timedelta(minutes=minutes_bump)
        next_bump_time = datetime.utcnow() + time_change

        with open("data/time_until_next_bump_dissoku", "wb") as datefile:
            pickle.dump(next_bump_time, datefile)

        self.s3_client.upload_file('data/time_until_next_bump_dissoku', "djtbot", 'bumping/time_until_next_bump_dissoku')

    async def loadtime(self):
        self.s3_client.download_file('djtbot', "bumping/time_until_next_bump_dissoku", 'data/time_until_next_bump_dissoku')

        with open("data/time_until_next_bump_dissoku", "rb") as datefile:
            next_bump_time = pickle.load(datefile)

        difference_in_time = next_bump_time - datetime.utcnow()
        minutes_left = int(difference_in_time.total_seconds() / 60)

        if minutes_left > 60 or minutes_left < 1:
            minutes_left = 1

        return minutes_left

    async def increment_leaderboard(self, userid):
        userid = str(userid)
        self.s3_client.download_file('djtbot', "bumping/dissoku upleaderboard.json", 'data/dissoku upleaderboard.json')

        with open("data/dissoku upleaderboard.json") as json_file:
            leaderboard_dict = json.load(json_file)

        if userid:
            leaderboard_dict[userid] = leaderboard_dict.get(userid, 0) + 1

            with open('data/dissoku upleaderboard.json', 'w') as json_file:
                json.dump(leaderboard_dict, json_file)

        self.s3_client.upload_file('data/dissoku upleaderboard.json', "djtbot", 'bumping/dissoku upleaderboard.json')

        pins = await self.msg_channel.pins()
        old_pins = []
        for old_pin in pins:
            if old_pin.author.id == self.bot.user.id:
                old_pins.append(old_pin)

        leaderboard_message = ["Bump leaderboard:"]
        edit_index = 0
        new_pins = []
        sorted_users = sorted(leaderboard_dict, key=leaderboard_dict.get, reverse=True)
        for index, current_userid in enumerate(sorted_users):
            position = index + 1
            userline = f"{position}. <@!{current_userid}> with {leaderboard_dict[current_userid]} bumps."
            leaderboard_message.append(userline)
            if len("\n".join(leaderboard_message)) > 1800:
                try:
                    await old_pins[edit_index].edit(content="\n".join(leaderboard_message))
                except IndexError:
                    new_pins.append(await self.msg_channel.send("\n".join(leaderboard_message)))
                edit_index += 1
                leaderboard_message = []

        if new_pins:
            for message in new_pins[::-1]:
                await message.pin()

        if userid:
            await self.msg_channel.send(f"Thanks for bumping <@!{userid}>. \n"
                                        f"You earned a point making your total score: **{leaderboard_dict[userid]}**\n"
                                        f"Your current position on the leaderboard is: **{sorted_users.index(userid) + 1}**\n"
                                        f"Check the channel pins for the leaderboard!")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def updateleaderboard(self, ctx):
        await self.increment_leaderboard(None)
        await ctx.send("Success.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id == 761562078095867916:
            await asyncio.sleep(4)
            for embed in message.embeds:
                userid = message.interaction.user.id
                if "をアップしたよ!" in embed.fields[0].name:
                    self.startwaiter.cancel()
                    self.waitminuteswaiter.cancel()
                    self.idlewaiter.cancel()
                    self.waiterindex = 0
                    self.starterindex = 0
                    self.bumperindex = 0
                    self.idleindex = 0

                    if self.bumpwaiter.is_running():
                        self.bumpwaiter.restart()
                    else:
                        self.bumpwaiter.start()

                    await self.increment_leaderboard(userid)
                    await self.savetime()

                elif "失敗しました" in embed.fields[0].name:
                    self.wait_time = float(re.findall(r"(\d\d?\d?)分", embed.fields[0].value)[0]) + 1
                    self.startwaiter.cancel()
                    self.idlewaiter.cancel()
                    self.bumpwaiter.cancel()
                    self.waiterindex = 0
                    self.starterindex = 0
                    self.bumperindex = 0
                    self.idleindex = 0

                    if self.waitminuteswaiter.is_running():
                        self.waitminuteswaiter.restart()
                    else:
                        self.waitminuteswaiter.start()

                    await self.savetime(int(self.wait_time))

    @tasks.loop(minutes=61.0)
    async def bumpwaiter(self):
        """ After succesfully bumping! """
        if self.bumperindex == 0:
            await self.msg_channel.send("Successfully bumped. Waiting for 60 minutes.")
            self.bumperindex = 1

        elif self.bumperindex == 1:
            await self.msg_channel.send(f"{self.bumprole.mention} Bump now with `/dissoku up`")
            self.idlewaiter.start()
            self.bumpwaiter.cancel()

    @tasks.loop(minutes=15.0)
    async def startwaiter(self):
        """ On bot startup. """
        if self.starterindex == 0:
            # await self.msg_channel.send(f"Bot restarted and loaded time of {self.minutes_until_next_bump} until next bump.")
            self.startwaiter.change_interval(minutes=float(self.minutes_until_next_bump))
            self.starterindex = 1
            self.startwaiter.restart()

        elif self.starterindex == 1:
            self.starterindex = 2

        elif self.starterindex == 2:
            await self.msg_channel.send(f"Bump now with `/dissoku up`")
            self.starterindex = 0
            self.idlewaiter.start()
            self.startwaiter.cancel()

    @tasks.loop(minutes=100.0)
    async def waitminuteswaiter(self):
        """ After getting Dissoku wait message."""
        if self.waiterindex == 0:
            await self.msg_channel.send(f"Can't bump yet. Waiting for {int(self.wait_time)} minutes.")
            self.waiterindex = 1
            self.waitminuteswaiter.change_interval(minutes=self.wait_time)
            self.waitminuteswaiter.restart()
        elif self.waiterindex == 1:
            self.waiterindex = 2
        elif self.waiterindex == 2:
            await self.msg_channel.send(f"Bump now with `/dissoku up`")
            self.waiterindex = 0
            self.idlewaiter.start()
            self.waitminuteswaiter.cancel()

    @tasks.loop(minutes=60.0)
    async def idlewaiter(self):
        """ After nothing has been done for some time. """
        if self.idleindex == 0:
            self.idleindex = 1
            self.time_idled = 0
        elif self.idleindex == 1:
            self.time_idled += 60
            if self.time_idled < 20:
                await self.msg_channel.send(f"Idled for {self.time_idled} minutes. Bump now with `/dissoku up`")
            if self.time_idled == 20:
                await self.msg_channel.send(f"{self.bumprole.mention} Idled for {self.time_idled} minutes. Bump now with `/dissoku up`")
            if self.time_idled > 20:
                await self.msg_channel.send(f"Idled for {self.time_idled} minutes. Bump now with `/dissoku up`")

def setup(bot):
    bot.add_cog(DissokuBumpCog(bot))