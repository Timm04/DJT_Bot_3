"""Cog for for join and leave messages and the presence status."""

import discord
from discord.ext import commands
import json

#############################################################
# Variables (Temporary)
with open(f"cogs/guild_data.json") as json_file:
    data_dict = json.load(json_file)
    main_guild_id = data_dict["guild_id"]

    send_welcome_message = True
    join_quiz_message_id = data_dict["join_quiz_1_id"]
    welcome_channel_id = data_dict["welcome_channel_id"]
    send_join_announcement = True
    otaku_channel_id = data_dict["otaku_channel_id"]

    give_join_role = True
    join_role_id = data_dict["unranked_role_id"]

    send_leave_message = True
    leave_message_channel_id = data_dict["otaku_channel_id"]

    quizranks = data_dict["quizranks"]

#############################################################

class BasicSetup(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # Welcome Message & Standard Role
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild.id == main_guild_id:
            if send_welcome_message:
                welcome_message_channel = self.bot.get_channel(join_quiz_message_id)
                instructions_channel = self.bot.get_channel(welcome_channel_id)
                welcomemessage = (f"Hello {member.mention}! Welcome to {member.guild.name}. "
                                  f"**Access to all channels is restricted to Japanese learners!**"
                                  f"\nTo join type `k!quiz n4 nodelay atl=10 14 size=80 mmq=2` "
                                  f"and get 14 points (max 1 failed question)."
                                  f"\nYou have unlimited tries."
                                  f" More Information in {instructions_channel.mention}"
                                  f"\n\nこんにちは{member.mention}さん! {member.guild.name}へようこそ"
                                  f"\nこのサーバーは日本語検定でN4級以上の日本語力がある方にのみ入室が許可されています。"
                                  f"\n`k!quiz n4 nodelay atl=10 14 size=80 mmq=2`と入力し、日本語のテストを開始してください。"
                                  f"\n合格点は14点、ミスは2回までです。何回でもチャレンジしてください。")

                await welcome_message_channel.send(welcomemessage, file=discord.File(r'data/Irasshaimase.mp4'))

            if send_join_announcement:
                announcement_channel = self.bot.get_channel(otaku_channel_id)
                await announcement_channel.send(f"<@!{member.id}> joined the server. "
                                                f"Account creation date: {str(member.created_at)[0:10]}")

            if give_join_role:
                join_role = member.guild.get_role(join_role_id)
                await member.add_roles(join_role)

    # Leave Message (with rank)
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.guild.id == main_guild_id:
            if send_leave_message:
                leave_message_channel = self.bot.get_channel(leave_message_channel_id)
                for role in member.roles:
                    if role.id in quizranks:
                        rankname = role.name
                await leave_message_channel.send(f"**{str(member)}** ({rankname}) just left the server.")

def setup(bot):
    bot.add_cog(BasicSetup(bot))