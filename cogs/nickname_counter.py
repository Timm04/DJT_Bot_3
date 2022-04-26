import typing as t
from dataclasses import dataclass
import discord
import boto3
import asyncio
from datetime import datetime
import json
import discord.errors
from discord.ext import commands
from discord.ext import tasks

#############################################################
with open(f"cogs/guild_data.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]
#############################################################


@dataclass
class NickRecord:
    user_id: str
    nickname_template: str
    last_reset: datetime

    def days_since_last_reset(self) -> int:
        now = datetime.utcnow()
        duration = now - self.last_reset
        return duration.days

    def current_nickname(self) -> str:
        days = self.days_since_last_reset()
        new_name = self.nickname_template.replace('XXXX', str(days), 1)
        return new_name

    def reset(self) -> None:
        self.last_reset = datetime.utcnow()


class NickName(commands.Cog):

    def __init__(self, bot):
        self.first_loop = True
        self.bot = bot
        self.s3_client = boto3.client('s3')

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guild_id)
        self.nickname_changer.start()

    def load_nick_record(self, user_id: str) -> t.Optional[NickRecord]:
        self.s3_client.download_file('djtbot', "nickdata.json", 'data/nickdata.json')

        with open(f"data/nickdata.json") as json_file:
            nick_dict = json.load(json_file)

        if user_id in nick_dict:
            last_reset_str, nickname_template = nick_dict[user_id]
            last_reset = datetime.strptime(last_reset_str, "%d.%m.%Y")
            return NickRecord(user_id, nickname_template, last_reset)
        else:
            return None

    def store_nick_record(self, nick_record: NickRecord) -> None:
        self.s3_client.download_file('djtbot', "nickdata.json", 'data/nickdata.json')
        with open(f"data/nickdata.json") as json_file:
            nick_dict = json.load(json_file)

        nick_dict[nick_record.user_id] = (nick_record.last_reset.strftime("%d.%m.%Y"), nick_record.nickname_template)

        with open('data/nickdata.json', 'w') as json_file:
            json.dump(nick_dict, json_file)

        self.s3_client.upload_file('data/nickdata.json', "djtbot", 'nickdata.json')

    def delete_nick_record(self, user_id: str) -> None:
        self.s3_client.download_file('djtbot', "nickdata.json", 'data/nickdata.json')
        with open(f"data/nickdata.json") as json_file:
            nick_dict = json.load(json_file)

        nick_dict.pop(user_id)

        with open('data/nickdata.json', 'w') as json_file:
            json.dump(nick_dict, json_file)

        self.s3_client.upload_file('data/nickdata.json', "djtbot", 'nickdata.json')

    def load_all_nick_records(self) -> t.List[NickRecord]:
        self.s3_client.download_file('djtbot', "nickdata.json", 'data/nickdata.json')

        with open(f"data/nickdata.json") as json_file:
            nick_dict = json.load(json_file)

        nick_records = []
        for user_id, (last_reset_str, nickname_template) in nick_dict.items():
            last_reset = datetime.strptime(last_reset_str, "%d.%m.%Y")
            nick_records.append(NickRecord(user_id, nickname_template, last_reset))

        return nick_records


    @commands.command()
    @commands.guild_only()
    async def ikillthedevil(self, ctx, *, nickname):
        """Day counting nickname. Include XXXX as placeholder."""

        nickname = str(nickname)

        if len(nickname) > 32:
            await ctx.send("Nickname is too long. Restrict yourself to 32 symbols.")
            return

        if not 'XXXX' in nickname:
            await ctx.send("Missing placeholder. Exiting...")
            return

        user_id = str(ctx.author.id)
        nick_record = self.load_nick_record(user_id)

        if nick_record is None:
            now = datetime.utcnow()
            nick_record = NickRecord(user_id, nickname, now)

        else:
            nick_record.nickname_template = nickname

        new_name = nick_record.current_nickname()
        self.store_nick_record(nick_record)

        try:
            await ctx.author.edit(nick=new_name)
        except discord.errors.Forbidden:
            await ctx.send("You cannot have a nickname role.")
            self.delete_nick_record(user_id)
        except AttributeError:
            await ctx.send("Please use this command inside the server.")
            return

        await ctx.send("Changed nickname.")

    @commands.command()
    @commands.guild_only()
    async def ifailed(self, ctx):
        """Reset the counter on a day counting nickname."""

        user_id = str(ctx.author.id)
        nick_record = self.load_nick_record(user_id)

        if nick_record is None:
            await ctx.send("User not found in data.")
            return

        nick_record.reset()
        new_name = nick_record.current_nickname()

        self.store_nick_record(nick_record)

        await ctx.author.edit(nick=new_name)
        await ctx.send("Reset counter.")

    @commands.command()
    @commands.guild_only()
    async def iquit(self, ctx):
        """Stop automatically changing your nickname."""

        user_id = str(ctx.author.id)
        try:
            self.delete_nick_record(user_id)
        except KeyError:
            return
        await ctx.author.edit(nick=None)
        await ctx.send("Deleted your nickname.")

    @tasks.loop(minutes=120.0)
    async def nickname_changer(self):
        if self.first_loop:
            self.first_loop = False

        else:
            for nick_record in self.load_all_nick_records():
                try:
                    user = self.myguild.get_member(int(nick_record.user_id))
                    if user:
                        nick_name = nick_record.current_nickname()
                        await user.edit(nick=nick_name)
                        await asyncio.sleep(10)

                except discord.errors.Forbidden:
                    pass

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def update_nicknames(self, ctx):
        for nick_record in self.load_all_nick_records():
            try:
                user = self.myguild.get_member(int(nick_record.user_id))
                if user:
                    print(f"Changing nickname for user {str(user)}")
                    nick_name = nick_record.current_nickname()
                    await user.edit(nick=nick_name)
                    await asyncio.sleep(1)

            except discord.errors.Forbidden:
                pass

        await ctx.send("Done.")


def setup(bot):
    bot.add_cog(NickName(bot))
