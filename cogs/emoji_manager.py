import asyncio

import discord
from discord.ext import commands
from discord.ext import tasks
import boto3
import json

#############################################################
# Variables (Temporary)
with open(f"cogs/guild_data.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]
    admin_role_ids = [data_dict["admin_role_id"], data_dict["mod_role_id"]]
    allowed_role_ids = data_dict["custom_emoji_permission"]

def is_admin_or_mod():
    async def predicate(ctx):
        run_command = False
        for role in ctx.author.roles:
            if role.id == admin_role_ids[0] or role.id == admin_role_ids[1]:
                run_command = True
        return run_command
    return commands.check(predicate)
#############################################################

class EmojiManagement(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.s3_client = boto3.client('s3')

    async def download_file(self, filename):
        self.s3_client.download_file("djtbot", f"{filename}", f"data/{filename}")

        with open(f"data/{filename}") as json_file:
            my_data = json.load(json_file)

        return my_data

    async def upload_file(self, my_data, filename):

        with open(f'data/{filename}', 'w') as json_file:
            json.dump(my_data, json_file)

        self.s3_client.upload_file(f"data/{filename}", "djtbot", f"{filename}")

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guild_id)
        self.give_emoji_role.start()

    async def has_full_emoji_permissions(self, member_roles):
        for role in member_roles:
            if role.id in admin_role_ids:
                return True

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, emojis_before, emojis_after):
        """Controls emoji changes. Mods and admins can perform all changes, while other users changes get reversed if
        they were not permitted."""
        log_channel = discord.utils.get(guild.channels, name="otaku")

        emoji_actions = [discord.AuditLogAction.emoji_update,
                         discord.AuditLogAction.emoji_delete,
                         discord.AuditLogAction.emoji_create]

        async for entry in guild.audit_logs(limit=5):
            performing_member = entry.user

            if performing_member.id == self.bot.user.id:
                print("Reverted emoji action.")
                return

            full_permissions = await self.has_full_emoji_permissions(performing_member.roles)

            if entry.action in emoji_actions:
                print(f"{performing_member} performed an emoji update.")

            ###########
            # Attempting to rename an emoji
            if entry.action == emoji_actions[0]:
                emoji_changed = await guild.fetch_emoji(entry.target.id)
                action_allowed = emoji_changed.user.id == performing_member.id

                if action_allowed or full_permissions:
                    await asyncio.sleep(2)
                    await log_channel.send(f"**{performing_member}** changed the emoji name **{entry.before.name}** to **{entry.after.name}**.")
                    return

                else:
                    await asyncio.sleep(2)
                    await log_channel.send(f"**{performing_member}** attempted to change the emoji name **{entry.before.name}** to **{entry.after.name}** (but was not permitted to).")
                    await asyncio.sleep(2)
                    await emoji_changed.edit(name=entry.before.name)
                    return

            ###########
            # Attempting to delete an emoji
            elif entry.action == emoji_actions[1]:
                emoji_deleted = [emoji for emoji in emojis_before if emoji not in emojis_after][0]

                if full_permissions:
                    await log_channel.send(f"**{performing_member}** just deleted the emoji **{emoji_deleted.name}**.")
                    return

                else:
                    await asyncio.sleep(2)
                    await log_channel.send(f"**{performing_member}** attempted to delete the emoji **{emoji_deleted.name}** (but was not permitted to).")
                    await asyncio.sleep(2)
                    emoji_deleted_image = await emoji_deleted.read()
                    await guild.create_custom_emoji(name=emoji_deleted.name, image=emoji_deleted_image)
                    await self.blacklist_member(performing_member)
                    return

            ###########
            # Attempting to create an emoji
            elif entry.action == emoji_actions[2]:
                emoji_created = entry.target
                all_emojis = await guild.fetch_emojis()
                user_owned_emoji = [emoji for emoji in all_emojis if emoji.user.id == performing_member.id]
                allowed_emoji_count = 15
                max_emoji_reached = len(user_owned_emoji) > allowed_emoji_count
                if full_permissions:
                    await log_channel.send(f"**{performing_member}** just created the emoji **{emoji_created.name}**.")
                    return
                elif not max_emoji_reached:
                    await log_channel.send(f"**{performing_member}** just created the emoji **{emoji_created.name}** ({allowed_emoji_count-len(user_owned_emoji)}/{allowed_emoji_count} slots left).")
                    return
                else:
                    await log_channel.send(f"**{performing_member}** just tried to create the emoji **{emoji_created.name}** but their maximum slots were reached.")
                    await emoji_created.delete()
                    return

    # @commands.Cog.listener()
    # async def on_guild_stickers_update(self, guild, stickers_before, stickers_after):
    #     log_channel = discord.utils.get(guild.channels, name="otaku")
    #
    #     sticker_actions = [discord.AuditLogAction.sticker_update,
    #                      discord.AuditLogAction.sticker_delete,
    #                      discord.AuditLogAction.sticker_create]
    #
    #     async for entry in guild.audit_logs(limit=5):
    #         performing_member = entry.user
    #
    #         if performing_member.id == self.bot.user.id:
    #             print("Reverted sticker action.")
    #             return
    #
    #         full_permissions = await self.has_full_emoji_permissions(performing_member.roles)
    #
    #         if entry.action in sticker_actions:
    #             print(f"{performing_member} performed a sticker update.")
    #
    #         ###########
    #         # Attempting to rename a sticker
    #         if entry.action == sticker_actions[0]:
    #             sticker_changed = await guild.fetch_sticker(entry.target.id)
    #             action_allowed = sticker_changed.user.id == performing_member.id
    #
    #             if action_allowed or full_permissions:
    #                 await asyncio.sleep(2)
    #                 await log_channel.send(f"**{performing_member}** changed the sticker name **{entry.before.name}** to **{entry.after.name}**.")
    #                 return
    #
    #             else:
    #                 await asyncio.sleep(2)
    #                 await log_channel.send(f"**{performing_member}** attempted to change the sticker name **{entry.before.name}** to **{entry.after.name}** (but was not permitted to).")
    #                 await asyncio.sleep(2)
    #                 await sticker_changed.edit(name=entry.before.name)
    #                 return
    #
    #         ###########
    #         # Attempting to delete an emoji
    #         elif entry.action == sticker_actions[1]:
    #             sticker_deleted = [sticker for sticker in stickers_before if sticker not in stickers_after][0]
    #
    #             full_permissions = False
    #             if full_permissions:
    #                 await log_channel.send(f"**{performing_member}** just deleted the sticker **{sticker_deleted.name}**.")
    #                 return
    #
    #             else:
    #                 await asyncio.sleep(2)
    #                 await log_channel.send(f"**{performing_member}** attempted to delete the sticker **{sticker_deleted.name}** (but was not permitted to).")
    #                 await asyncio.sleep(2)
    #                 sticker_delete_image = await sticker_deleted.url
    #
    #                 await guild.create_sticker(name=sticker_deleted.name, emoji=sticker_deleted.emoji, file=sticker_delete_image)
    #                 await self.blacklist_member(performing_member)
    #                 return

    async def blacklist_member(self, member):
        log_channel = discord.utils.get(self.myguild.channels, name="otaku")
        emoji_role = discord.utils.get(self.myguild.roles, name="Emoji")
        await asyncio.sleep(1)
        await member.remove_roles(emoji_role)
        await asyncio.sleep(1)
        await log_channel.send(f"**{member}** attempted to delete an emoji and lost emoji permissions or was otherwise blacklisted.")

        blacklisted_user_ids = await self.download_file("emoji_blacklisted_users.json")
        blacklisted_user_ids.append(member.id)
        await self.upload_file(blacklisted_user_ids, "emoji_blacklisted_users.json")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def unblacklist_member(self, ctx, user_id):
        user_id = int(user_id)
        blacklisted_user_ids = await self.download_file("emoji_blacklisted_users.json")
        blacklisted_user_ids.remove(user_id)
        await self.upload_file(blacklisted_user_ids, "emoji_blacklisted_users.json")
        await ctx.send(f"Unblacklisted user with the id: {user_id}")

    @tasks.loop(minutes=60.0)
    async def give_emoji_role(self):
        legal_emoji_roles = [role for role in self.myguild.roles if role.id in allowed_role_ids]
        emoji_role = discord.utils.get(self.myguild.roles, name="Emoji")
        blacklisted_user_ids = await self.download_file("emoji_blacklisted_users.json")

        for role in legal_emoji_roles:
            for member in role.members:
                if emoji_role not in member.roles and member.id not in blacklisted_user_ids:
                    await asyncio.sleep(1)
                    await member.add_roles(emoji_role)
                    print(f"Gave emoji role to {member.name}")

    @commands.command(hidden=True)
    @is_admin_or_mod()
    async def give_emoji(self, ctx, user_id):
        member = self.myguild.get_member(int(user_id))
        try:
            await self.unblacklist_member(ctx, user_id)
        except ValueError:
            pass
        emoji_role = discord.utils.get(self.myguild.roles, name="Emoji")
        await member.add_roles(emoji_role)
        await ctx.send(f"Gave {member} the Emoji role.")

    @commands.command(hidden=True)
    @is_admin_or_mod()
    async def remove_emoji(self, ctx, user_id):
        member = self.myguild.get_member(int(user_id))
        await self.blacklist_member(member)
        emoji_role = discord.utils.get(self.myguild.roles, name="Emoji")
        await member.remove_roles(emoji_role)
        await ctx.send(f"Removed the Emoji role from {member}.")

def setup(bot):
    bot.add_cog(EmojiManagement(bot))