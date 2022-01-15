"""Cog to regularly save roles of all members."""

import discord
from discord.ext import commands
from discord.ext import tasks
import boto3
import json

with open(f"cogs/guild_data.json") as json_file:
    data_dict = json.load(json_file)
    to_save_server_id = data_dict["guild_id"]

class RankSaver(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.s3_client = boto3.client('s3')

    @commands.Cog.listener()
    async def on_ready(self):
        self.rank_saver.start()

    @tasks.loop(minutes=10.0)
    async def rank_saver(self):
        """Regularly saves all member roles to a json file."""
        self.s3_client.download_file('djtbot', "rolesdata.json", 'data/rolesdata.json')

        to_save_server = self.bot.get_guild(to_save_server_id)

        with open(f"data/rolesdata.json") as json_file:
            user_dict = json.load(json_file)

        all_members = [member for member in to_save_server.members if member.bot is False]
        for member in all_members:
            member_roles = [str(role) for role in member.roles if
                            role.name != "@everyone" and role.name != '農奴 / Unranked' and role.name != "Server Booster"]
            user_dict[str(member.id)] = member_roles

        with open(f'data/rolesdata.json', 'w') as json_file:
            json.dump(user_dict, json_file)

        self.s3_client.upload_file(f"data/rolesdata.json", "djtbot", f"rolesdata.json")

def setup(bot):
    bot.add_cog(RankSaver(bot))