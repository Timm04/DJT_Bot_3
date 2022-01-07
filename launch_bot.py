"""This file will launch the bot and load all cogs."""

import discord
from discord.ext import commands
import os
import boto3

intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.members = True
djtbot = commands.Bot(command_prefix='$', intents=intents)

@djtbot.check
def check_guild(ctx):
    try:
        return ctx.guild.id == 862488397371932672 # Current guild id
    except AttributeError:
        return True

for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        djtbot.load_extension(f'cogs.{filename[:-3]}')
        print(f"Loaded the following cog: {filename}")

# djtbot.load_extension(f'cogs.create_djt')

s3_client = boto3.client('s3')
s3_client.download_file('newdjtbot', "token.txt", 'token.txt')

with open("token.txt") as token_file:
    bot_token = token_file.read()

djtbot.run(bot_token)


