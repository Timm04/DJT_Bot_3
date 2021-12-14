"""Language Restriction"""
import urllib.error

import discord
from discord.ext import commands
from textblob import TextBlob
import json
import asyncio
import re

with open(f"cogs/guild_data.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]


class LanguageDetect(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.active = False
        self.remove_res = [re.compile(r'<#\d+>'), re.compile(r'<:\w+:\d+>'), re.compile(r'<@!?\d+>'),
                           re.compile(r'https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)'),
                           re.compile(u'\U0001F600-\U0001F64F'), re.compile(u'\U0001F300-\U0001F5FF'),
                           re.compile(u'\U0001F680-\U0001F6FF'), re.compile(u'\U0001F1E0-\U0001F1FF')]

    async def format_message(self, message: discord.Message):
        allowed_messages = ["ｗｗｗ", "ｗｗ", "www", "ww", "orz"]
        restricted_channel_names = ["otaku", "elite-otaku", "offtopic", "nihongo", "vn", "books", "manga",
                                   "beginner-questions"]

        new_message = message.content.strip().replace("\n", "")
        for regexp in self.remove_res:
            new_message = regexp.sub('', new_message)

        for text in allowed_messages:
            new_message = new_message.replace(text, '')

        for command in self.bot.commands:
            new_message = new_message.replace('$' + command.name, '')

        try:
            if message.guild.id != guild_id:
                return False
        except AttributeError:
            return False

        if message.channel.name not in restricted_channel_names:
            return False
        elif len(new_message) < 3:
            return False
        elif new_message.isnumeric():
            return
        else:
            return new_message

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id == 902684355720257606 or not self.active:
            return
        check_message = await self.format_message(message)
        if check_message:
            allowed_languages = ["ja", "zh-CN"]
            my_textblob = TextBlob(message.content.strip())
            try:
                language = my_textblob.detect_language()
                await asyncio.sleep(1)
            except urllib.error.HTTPError:
                print("Broken message:", message.content)
                return
            # Eidan Eigo-Sibari
            if message.author.id == 527476475042070528 and language != 'en':
                print(f"'{message.content}' deleted by Eidan. Language: {language}")
                await asyncio.sleep(1)
                await message.delete()
                await asyncio.sleep(1)
                await message.channel.send(f"{message.author.mention} You must speak in English.")
                return
            elif language not in allowed_languages and message.author.id != 527476475042070528:
                print(f"'{message.content}' deleted. Language: {language}")
                await asyncio.sleep(1)
                await message.delete()
                await asyncio.sleep(1)
                await message.channel.send(f"{message.author.mention} 外国語は禁止です！　日本語でお願いしますね　：）。 ")
                return
            else:
                return

    @commands.Cog.listener()
    async def on_message_edit(self, message_before: discord.Message, message_after : discord.Message):
        await self.on_message(message_after)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def toggle(self, ctx):
        if self.active:
            self.active = False
            await ctx.send("Deactivated language block.")
        else:
            self.active = True
            await ctx.send("Activated language block.")

def setup(bot):
    bot.add_cog(LanguageDetect(bot))