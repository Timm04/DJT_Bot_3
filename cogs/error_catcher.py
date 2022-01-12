"Some error handling."
import discord
import re
import json
from discord.ext import commands

#############################################################
# Variables (Temporary)
with open(f"cogs/guild_data.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]
    admin_user_id = data_dict["kaigen_user_id"]
    quizranks = data_dict["quizranks"]
    mycommands = data_dict["mycommands"]
    mycommands = {int(key): value for key, value in mycommands.items()}

#############################################################

class ErrorHandler(commands.Cog):
    """Commands in relation to the Quiz."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guild_id)

        admin_user = self.myguild.get_member(admin_user_id)
        await admin_user.create_dm()
        self.private_admin_channel = admin_user.dm_channel

        await self.private_admin_channel.send("Bot started.")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing the following argument: {error.param}")
            return
        elif isinstance(error, commands.errors.CommandNotFound):
            await ctx.send(f"That command was not found.")
            return
        elif isinstance(error, commands.errors.PrivateMessageOnly):
            await ctx.send(f"Please use this command in PM!")
            return
        elif isinstance(error, commands.errors.MaxConcurrencyReached):
            await ctx.send("Another user is already using this command! Only one concurrent session allowed...")
            return
        elif ctx.command and ctx.command.name == "levelup":
            await ctx.send(f"I am unable to send you a message {ctx.author.mention}. Please enable private messages.\n"
                           f"You can use the following command for your next level-up:")
            member = await self.myguild.fetch_member(ctx.author.id)
            for role in member.roles:
                if role.id in quizranks:
                    # String is cut down for easy copy and paste.
                    try:
                        currentcommand = re.search(r"`(.*)`", mycommands[role.id]).group(1)
                    except AttributeError:
                        await ctx.send("You have reached the highest level.")
                    await ctx.send(currentcommand)
            return

        else:
            await self.private_admin_channel.send(f"{str(error)}\n\nTriggered by: `{ctx.message.content}`\n"
                                                  f"Here: {ctx.message.jump_url}")
            raise error

def setup(bot):
    bot.add_cog(ErrorHandler(bot))