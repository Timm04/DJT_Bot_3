"""Cog for the book club"""
import discord
from discord.ext import commands
import re
import json

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

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guild_id)

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

        for role in self.myguild.roles:
            if str(role).endswith("📚") and len(role.members) == 0:
                await role.delete(reason="No users with role.")

def setup(bot):
    bot.add_cog(BookClub(bot))