import asyncio
import os
import discord
from discord.ext import commands
from discord.ext import tasks
import json
import boto3
import botocore.exceptions
from datetime import timedelta

#############################################################
# Variables (Temporary)
with open(f"cogs/guild_data.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]

#############################################################

def has_permission():
    async def predicate(ctx: commands.Context):
        allowed_roles = ["Mod", "Admin", "Helper"]
        for role in ctx.author.roles:
            if role.name in allowed_roles:
                return True
        return False
    return commands.check(predicate)

class Moderation(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.s3_client = boto3.client('s3')
        self.action_count = dict()

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guild_id)
        self.myguild: discord.Guild

        self.otaku_channel = discord.utils.get(self.myguild.channels, name="otaku")
        self.mod_channel = discord.utils.get(self.myguild.channels, name="mod")

        self.clear_action_count.start()

    async def check_valid_target(self, ctx, target_member: discord.Member):
        protected_roles = ["Mod", "Admin", "Helper"]
        for role in target_member.roles:
            if role.name in protected_roles:
                await ctx.send("You cannot perform moderator actions on this user.")
                return False
        return True

    async def increment_mod_action(self, ctx):
        self.action_count[ctx.author.id] = self.action_count.get(ctx.author.id, 0) + 1
        if self.action_count[ctx.author.id] > 5:
            await ctx.send(f"{ctx.author.mention} You are performing too many moderator actions too fast. Please wait until you can perform more moderator actions.")
            return False
        else:
            return True

    async def ask_reason(self, ctx: commands.Context, action_info):

        await ctx.send(f"{ctx.author.mention} Please specify the reason for this moderator action:")

        def response_check(message):
            return message.author.id == ctx.author.id

        try:
            message = await self.bot.wait_for('message', timeout=60.0, check=response_check)
        except:
            await ctx.send(f"{ctx.author.mention} As you did not specify a reason the moderator action was not performed.")
            return

        reason = message.content
        attachments = message.attachments
        if attachments:
            files = [await attachment.to_file() for attachment in attachments]
            await self.mod_channel.send(f"{action_info}\n`{reason}`\n{ctx.message.jump_url}", files=files)
        else:
            await self.mod_channel.send(f"{action_info}\n`{reason}`\n{ctx.message.jump_url}")
        return message

    async def get_member(self, ctx, user_mention):
        target_id = int("".join(filter(str.isnumeric, user_mention)))
        target_member = self.myguild.get_member(target_id)

        if not await self.check_valid_target(ctx, target_member):
            return False

        else:
            return target_member

    @commands.command(hidden=True)
    @has_permission()
    async def mute(self, ctx, user_mention, hours):

        target_member = await self.get_member(ctx, user_mention)
        if not target_member:
            return

        if not hours.isnumeric():
            await ctx.send("Please specify the number of hours to mute this user.")
            return

        if int(hours) > 72:
            await ctx.send("You can mute users for a maximum of 72 hours.")
            return

        if not await self.increment_mod_action(ctx):
            return

        action_info = f"**MODERATOR LOG**\n{ctx.author.mention} just muted {target_member.mention} for {hours} hours with the following reason:"
        if not await self.ask_reason(ctx, action_info):
            return

        hours_to_mute = timedelta(hours=int(hours))
        await target_member.timeout_for(hours_to_mute)
        await ctx.send(f"{ctx.author.mention} just muted {target_member.mention} for {int(hours)} hours.")

    @commands.command(hidden=True)
    @has_permission()
    async def purge(self, ctx, user_mention, message_count):

        target_member = await self.get_member(ctx, user_mention)
        if not target_member:
            return

        if not message_count.isnumeric():
            await ctx.send("Please specify the number of messages to delete.")
            return

        if int(message_count) > 100:
            await ctx.send("You can only delete a maximum of 100 messages")
            return

        if not await self.increment_mod_action(ctx):
            return

        action_info = f"**MODERATOR LOG**\n{ctx.author.mention} just deleted {message_count} messages from {target_member.mention} in the channel {ctx.channel.name} with the following reason:"
        if not await self.ask_reason(ctx, action_info):
            return

        deletion_counter = 0
        def purge_condition(message: discord.Message):
            if message.author.id == target_member.id:
                nonlocal deletion_counter
                deletion_counter += 1
                if deletion_counter < int(message_count):
                    return True
                else:
                    return False
            else:
                return False

        messages = await ctx.channel.purge(limit=1000, check=purge_condition)
        message_content = "\n".join([message.content for message in messages])

        with open(f'data/deleted_message_content.txt', 'w') as text_file:
            text_file.write(message_content)

        await self.mod_channel.send(file=discord.File("data/deleted_message_content.txt"))
        os.remove("data/deleted_message_content.txt")

        await ctx.send(f"{ctx.author.mention} just deleted the last {message_count} messages from {target_member.mention}.")

    @commands.command(hidden=True)
    @has_permission()
    async def delete(self, ctx, message_id):

        message_to_delete = await ctx.channel.fetch_message(message_id)

        target_member = await self.get_member(ctx, str(message_to_delete.author.id))
        if not target_member:
            return

        if not message_id.isnumeric():
            await ctx.send("Please properly specify the message id.")
            return

        if message_to_delete.pinned:
            await ctx.send("You can't delete pinned messages")
            return

        if not await self.increment_mod_action(ctx):
            return

        action_info = f"**MODERATOR LOG**\n{ctx.author.mention} just deleted a message from {target_member.mention} in the channel {message_to_delete.channel.name} with the following reason:"

        if not await self.ask_reason(ctx, action_info):
            return

        message_content = f"The message had {len(message_to_delete.attachments)} attachments. Text content: \n{message_to_delete.content}"

        with open(f'data/deleted_message_content.txt', 'w') as text_file:
            text_file.write(message_content)

        await self.mod_channel.send(file=discord.File("data/deleted_message_content.txt"))
        os.remove("data/deleted_message_content.txt")

        await message_to_delete.delete()
        await ctx.send(f"{ctx.author.mention} just deleted a message from {target_member.mention}.")

    
    async def get_warnings(self):
        try:
            self.s3_client.download_file('djtbot', 'warning_count.json', f'data/warning_count.json')
        except botocore.exceptions.ClientError:
            try:
                with open(f"data/warning_count.json") as json_file:
                    data_dict = json.load(json_file)
                    return data_dict
            except FileNotFoundError:
                empty_dict = dict()
                return empty_dict

        with open(f"data/warning_count.json") as json_file:
            data_dict = json.load(json_file)

        return data_dict

    async def push_warnings(self, data_dict):
        with open(f'data/warning_count.json', 'w') as json_file:
            json.dump(data_dict, json_file)
        self.s3_client.upload_file(f'data/warning_count.json', "djtbot", f'warning_count.json')
        
    @commands.command(hidden=True)
    @has_permission()
    async def warn(self, ctx, user_mention):

        target_member = await self.get_member(ctx, user_mention)
        if not target_member:
            return

        if not await self.increment_mod_action(ctx):
            return

        action_info = f"**MODERATOR LOG**\n{ctx.author.mention} just gave {target_member.mention} a warning with the following reason:"
        warning_message = await self.ask_reason(ctx, action_info)
        if not warning_message:
            return

        warning_dict = await self.get_warnings()
        warning_dict[str(target_member.id)] = warning_dict.get(str(target_member.id), 0) + 1
        warning_count = warning_dict[str(target_member.id)]
        await self.push_warnings(warning_dict)

        await ctx.send(f"{ctx.author.mention} just gave the user {target_member.mention} a warning bringing their "
                       f"total warnings to **{warning_count}** with the following reason: ``{warning_message.content}``")

    @commands.command(hidden=True)
    @has_permission()
    async def kick(self, ctx, user_mention):

        target_member = await self.get_member(ctx, user_mention)
        if not target_member:
            return

        if not await self.increment_mod_action(ctx):
            return

        warning_dict = await self.get_warnings()
        warning_dict[str(target_member.id)] = warning_dict.get(str(target_member.id), 0) + 1
        warning_count = warning_dict[str(target_member.id)]

        if warning_count <= 3:
            await ctx.send(f"{ctx.author.mention} You can only kick people with more than 3 warnings.")
            return

        action_info = f"**MODERATOR LOG**\n{ctx.author.mention} just kicked {target_member.mention} (`{str(target_member)}` with id: `{target_member.id}`) with the following reason:"
        warning_message = await self.ask_reason(ctx, action_info)
        if not warning_message:
            return

        await target_member.create_dm()
        private_channel = target_member.dm_channel
        try:
            await private_channel.send(f"You were kicked from {ctx.guild.name} by moderator {str(ctx.author)} for the following reason: `{warning_message.content}`"
                                       f"\n You can rejoin through the following link: https://animecards.site/discord/")
        except discord.errors.Forbidden:
            pass

        await ctx.send(f"{ctx.author.mention} just kicked the user {target_member.mention} (`{str(target_member)}` with id: `{target_member.id}`).")
        await target_member.kick(reason=warning_message.content)

    @tasks.loop(minutes=60.0)
    async def clear_action_count(self):
        self.action_count = dict()

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def clear_warnings(self, ctx, user_mention):
        target_member = await self.get_member(ctx, user_mention)
        warning_dict = await self.get_warnings()
        warning_dict[str(target_member.id)] = 0
        await self.push_warnings(warning_dict)
        await ctx.send("Done.")

def setup(bot):
    bot.add_cog(Moderation(bot))
