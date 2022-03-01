"""Cog for the book club"""
import asyncio
import discord
from discord.ext import commands
from discord.ext import tasks
import re
import json
import boto3

#############################################################
# Variables (Temporary)

with open(f"cogs/guild_data.json") as json_file:
    data_dict = json.load(json_file)

    guild_id = data_dict["guild_id"]
    nullposter_user_id = data_dict["nullposter_id"]
    admin_id = data_dict["kaigen_user_id"]

#############################################################

class BookClub(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.s3_client = boto3.client('s3')
        self.fname = "book_leaderboard.json"

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guild_id)
        self.make_leaderboard.start()
        self.give_roles.start()

    @commands.command(hidden=True)
    async def setbooks(self, ctx, mention, point_count):
        if not ctx.author.id == nullposter_user_id:
            if not ctx.author.id == admin_id:
                return

        mentionid = re.findall(r"(\d+)", mention)[0]
        mention_user = await self.myguild.fetch_member(mentionid)

        point_count = int(point_count)

        for role in mention_user.roles:
            if str(role).endswith("📚"):
                await mention_user.remove_roles(role)

        if not point_count == 0:
            book_reward_role = discord.utils.get(self.myguild.roles, name=f"{point_count}📚")
            if not book_reward_role:
                reference_pos_role = discord.utils.get(self.myguild.roles, name=f"✓✓")
                reference_pos = reference_pos_role.position - 1

                book_reward_role = await self.myguild.create_role(name=f"{point_count}📚", colour=discord.Colour(6713472))
                positions = {book_reward_role: reference_pos}
                await self.myguild.edit_role_positions(positions)

            await mention_user.add_roles(book_reward_role)

        if point_count == 0:
            leaderboard = self.pull_all_records()
            del leaderboard[mentionid]
            self.push_all_records(leaderboard)

        for role in self.myguild.roles:
            if str(role).endswith("📚") and len(role.members) == 0:
                await role.delete(reason="No users with role.")

    def pull_all_records(self):
        self.s3_client.download_file('djtbot', self.fname, f'data/{self.fname}')
        with open(f"data/{self.fname}") as json_file:
            manga_dict = json.load(json_file)
        return manga_dict

    def push_all_records(self, manga_dict):
        with open(f'data/{self.fname}', 'w') as json_file:
            json.dump(manga_dict, json_file)
        self.s3_client.upload_file(f'data/{self.fname}', "djtbot", f'{self.fname}')

    @tasks.loop(minutes=10)
    async def make_leaderboard(self):
        book_roles = [role for role in self.myguild.roles if role.name.endswith("📚")]

        leaderboard = self.pull_all_records()

        for role in book_roles:
            for user in role.members:
                leaderboard[str(user.id)] = role.name

        self.push_all_records(leaderboard)

        book_channel = discord.utils.get(self.myguild.channels, name="books")

        pins = await book_channel.pins()
        old_pins = [pin for pin in pins if pin.content.startswith("LEADERBOARD")]
        new_pins = []
        sorted_leaderboard = sorted(leaderboard.items(), key=lambda item: int(item[1][:-1]), reverse=True)
        message_count = 0
        rank = 0
        msg = "LEADERBOARD:\n"
        for entry in sorted_leaderboard:
            msg += f'{rank + 1}. <@!{int(entry[0])}> : {entry[1][:-1]} BP\n'
            rank += 1
            if len(msg) > 1800:
                try:
                    await old_pins[message_count].edit(content=msg)
                except IndexError:
                    new_pins.append(await book_channel.send(msg))
                message_count += 1
                msg = ''
        if msg:
            try:
                await old_pins[message_count].edit(content=msg)
            except IndexError:
                new_pins.append(await book_channel.send(msg))

        if new_pins:
            for m in new_pins[::-1]:
                await m.pin()

    @tasks.loop(minutes=10)
    async def give_roles(self):
        leaderboard = self.pull_all_records()
        for user_data in leaderboard.items():
            user = self.myguild.get_member(int(user_data[0]))
            if user:
                for role in user.roles:
                    if role.name == user_data[1]:
                        return

                book_reward_role = discord.utils.get(self.myguild.roles, name=user_data[1])
                if not book_reward_role:
                    reference_pos_role = discord.utils.get(self.myguild.roles, name=f"✓✓")
                    reference_pos = reference_pos_role.position - 1

                    book_reward_role = await self.myguild.create_role(name=user_data[1],
                                                                      colour=discord.Colour(6713472))
                    positions = {book_reward_role: reference_pos}
                    await self.myguild.edit_role_positions(positions)

                await user.add_roles(book_reward_role)

    @commands.command(hidden=True)
    async def reposition_book_roles(self, ctx):
        book_roles = []
        for role in ctx.guild.roles:
            if role.name.endswith("📚"):
                book_roles.append(role)

        reference_pos_role = discord.utils.get(self.myguild.roles, name=f"✓✓")
        reference_pos = reference_pos_role.position - 1
        positions = dict()

        for role in book_roles:
            positions[role] = reference_pos
            reference_pos -= 1

        await self.myguild.edit_role_positions(positions)






def setup(bot):
    bot.add_cog(BookClub(bot))