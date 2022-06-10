"""Cog for for join and leave messages and the presence status."""
import discord
from discord.ext import commands
import json
import boto3
import botocore.exceptions


#############################################################
# Variables (Temporary)
with open(f"cogs/guild_data.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]

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

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guild_id)
        self.s3_client = boto3.client('s3')

    def pull_all_records(self, fname):
        try:
            self.s3_client.download_file('djtbot', fname, f'data/{fname}')
        except botocore.exceptions.ClientError:
            try:
                with open(f"data/{fname}") as json_file:
                    data_dict = json.load(json_file)
                    return data_dict
            except FileNotFoundError:
                empty_dict = dict()
                return empty_dict

        with open(f"data/{fname}") as json_file:
            data_dict = json.load(json_file)

        return data_dict

    def push_all_records(self, data_dict, fname):
        with open(f'data/{fname}', 'w') as json_file:
            json.dump(data_dict, json_file)
        self.s3_client.upload_file(f'data/{fname}', "djtbot", f'{fname}')

    # Welcome Message & Standard Role
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild.id == guild_id:
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

    async def increment_leave_count(self, member: discord.Member):
        if "農奴 / Unranked" in [role.name for role in member.roles]:
            return 0
        leave_count_dict = self.pull_all_records("leave_count.json")
        leave_count_dict[str(member.id)] = leave_count_dict.get(str(member.id), 0) + 1
        self.push_all_records(leave_count_dict, "leave_count.json")
        return leave_count_dict[str(member.id)]

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def clearleavecount(self, ctx, member_id):
        leave_count_dict = self.pull_all_records("leave_count.json")
        leave_count_dict[member_id] = 0
        self.push_all_records(leave_count_dict, "leave_count.json")
        await ctx.send("Done.")

    # Leave Message (with rank)
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.guild.id == guild_id:
            if send_leave_message:
                leave_message_channel = self.bot.get_channel(leave_message_channel_id)
                leave_count = await self.increment_leave_count(member)
                if leave_count >= 5:
                    await member.ban(reason="Leave Coping.")
                    await leave_message_channel.send(f"{str(member)} has been banned for leave coping..")
                for role in member.roles:
                    if role.id in quizranks:
                        rankname = role.name
                await leave_message_channel.send(f"**{str(member)}** ({rankname}) just left the server. ({leave_count}/5)")

def setup(bot):
    bot.add_cog(BasicSetup(bot))