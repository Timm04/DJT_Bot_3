"""Cog for rank restoration, custom rank creation and similar."""

import discord
from discord.ext import commands
from discord.ext import tasks
import boto3
import json
import asyncio
import re

#############################################################
# Variables (Temporary)
with open(f"cogs/guild_data.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]
    unranked_role_id = data_dict["unranked_role_id"]
    announcement_channel_id = data_dict["otaku_channel_id"]
    quizranks = data_dict["quizranks"]
    custom_role_permission_role_ids = data_dict["custom_role_permission"]
    position_reference_role_id = data_dict["position_reference_role_id"]

#############################################################
class RankManagement(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.s3_client = boto3.client('s3')

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guild_id)
        self.roleremover.start()

    async def download_file(self, filename):
        self.s3_client.download_file("djtbot", f"ranks/{filename}", f"data/{filename}")

        with open(f"data/{filename}") as json_file:
            data_dict = json.load(json_file)

        return data_dict

    async def upload_file(self, data_dict, filename):

        with open(f'data/{filename}', 'w') as json_file:
            json.dump(data_dict, json_file)

        self.s3_client.upload_file(f"data/{filename}", "djtbot", f"ranks/{filename}")
        print("Uploaded file.")


    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild.id == guild_id:
            announcement_channel = self.bot.get_channel(announcement_channel_id)
            await asyncio.sleep(5)
            self.s3_client.download_file('djtbot', "rolesdata.json", 'data/rolesdata.json')

            with open(f"data/rolesdata.json") as json_file:
                rolesdict = json.load(json_file)

            memberid = str(member.id)

            if memberid in rolesdict:
                if len(rolesdict[memberid]) >= 1:
                    if "Muted" not in rolesdict[memberid]:
                        unranked_role = self.myguild.get_role(unranked_role_id)
                        await member.remove_roles(unranked_role)
                    roles_to_restore = []
                    for role_string in rolesdict[memberid]:
                        await asyncio.sleep(1)
                        current_role = discord.utils.get(member.guild.roles, name=role_string)
                        if current_role:
                            roles_to_restore.append(current_role)

                    await member.add_roles(*roles_to_restore)
                    await announcement_channel.send(f"Restored **{', '.join(str(role) for role in roles_to_restore)}** for <@!{member.id}>.")

    @commands.command()
    async def makerole(self, ctx, role_name, color_code):
        """
        `<role_name>` `<#color_code>` Create a custom role (for 大公+)
        """
        # Check if eligible
        member = await self.myguild.fetch_member(ctx.author.id)
        custom_role_permission = False
        for role in member.roles:
            if role.id in custom_role_permission_role_ids:
                custom_role_permission = True

        if not custom_role_permission:
            await ctx.send("You don't have custom role permission. Please pass the 大公 quiz.")
            return

        # Check if valid arguments
        if len(role_name) > 7:
            await ctx.send("Please use a shorter role name. Restrict yourself to 7 symbols.")
            return

        if role_name == "大王":
            await ctx.send("Invalid role name.")
            return

        if role_name == "大公":
            await ctx.send("Invalid role name.")
            return

        if role_name == "日本人":
            await ctx.send("You are not!")
            return

        color_match = re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', color_code)
        if not color_match:
            await ctx.send("Please enter a valid hex color code.")
            return

        actual_color_code = int(re.findall(r'^#((?:[0-9a-fA-F]{3}){1,2})$', color_code)[0], base=16)

        custom_roles_dict = await self.download_file("customroles.json")

        string_member_id = str(ctx.author.id)

        custom_role_id = custom_roles_dict.get(string_member_id)
        custom_role = self.myguild.get_role(custom_role_id)
        if custom_role_id and custom_role:
            await custom_role.edit(name=role_name, colour=discord.Colour(actual_color_code))
            await member.add_roles(custom_role)
            await ctx.send("Updated role.")

        else:
            position_ref_role = self.myguild.get_role(position_reference_role_id)
            custom_role = await self.myguild.create_role(name=role_name, colour=discord.Colour(actual_color_code))
            positions = {custom_role: position_ref_role.position + 1}
            await self.myguild.edit_role_positions(positions)
            await member.add_roles(custom_role)
            custom_roles_dict[string_member_id] = custom_role.id
            await ctx.send("Created role.")

        await self.upload_file(custom_roles_dict, "customroles.json")

    @commands.command()
    async def removerole(self, ctx):
        """Delete the custom role."""
        custom_roles_dict = await self.download_file("customroles.json")
        custom_role_id = custom_roles_dict.get(str(ctx.author.id))
        custom_role = self.myguild.get_role(custom_role_id)
        member = await self.myguild.fetch_member(ctx.author.id)
        await member.remove_roles(custom_role)
        await custom_role.delete()
        custom_roles_dict.pop(str(ctx.author.id))
        await self.upload_file(custom_roles_dict, "customroles.json")

    @commands.command()
    async def makeicon(self, ctx: commands.Context):
        """Create an icon for your custom role. Has to be a png with 1x1 resolution."""
        member = await self.myguild.fetch_member(ctx.author.id)
        custom_role_permission = False
        for role in member.roles:
            if role.id in custom_role_permission_role_ids:
                custom_role_permission = True

        if not custom_role_permission:
            await ctx.send("You don't have custom role permission. Please pass the 大公 quiz.")
            return

        if not ctx.message.attachments:
            await ctx.send("Please attach the image to the command call.")
            return

        icon = ctx.message.attachments[0]
        if icon.content_type != "image/png":
            await ctx.send("Please use a .png image.")
            return

        if not icon.height == icon.width:
            await ctx.send("Height and width have to be equal.")
            return

        custom_roles_dict = await self.download_file("customroles.json")
        user_id = str(ctx.author.id)

        if user_id not in custom_roles_dict:
            await ctx.send("You don't seem to have a custom role set. Please set one with `$makerole`.")
            return

        custom_role = self.myguild.get_role(custom_roles_dict[user_id])
        icon_bytes = await icon.read()

        try:
            await custom_role.edit(icon=icon_bytes)

        except discord.errors.HTTPException:
            await ctx.send("The file has to be smaller than 256kb.")
            return

        await ctx.send("Added the icon to your role.")

    @tasks.loop(minutes=120.0)
    async def roleremover(self):
        custom_roles_dict = await self.download_file("customroles.json")
        for string_id in custom_roles_dict:
            user_id = int(string_id)
            role_id = int(custom_roles_dict[string_id])
            custom_role = self.myguild.get_role(role_id)
            custom_role_permission = False

            # If custom role doesn't exist.
            if not custom_role:
                custom_roles_dict.pop(string_id)
                await self.upload_file(custom_roles_dict, "customroles.json")
                return

            # Get member
            member = self.myguild.get_member(user_id)
            if not member:
                try:
                    member = await self.myguild.fetch_member(user_id)
                except discord.errors.HTTPException:
                    member = None

            # If member left the server
            if not member:
                await custom_role.delete()
                custom_roles_dict.pop(string_id)
                await self.upload_file(custom_roles_dict, "customroles.json")
                return

            # Role not assigned
            if len(custom_role.members) == 0:
                await custom_role.delete()
                custom_roles_dict.pop(string_id)
                await self.upload_file(custom_roles_dict, "customroles.json")
                return

            # Check if role permissions still exist
            for role in member.roles:
                if role.id in custom_role_permission_role_ids:
                    custom_role_permission = True

            # Role permissions gone
            if not custom_role_permission:
                await member.remove_roles(custom_role)
                await custom_role.delete()
                custom_roles_dict.pop(string_id)
                await self.upload_file(custom_roles_dict, "customroles.json")
                return

def setup(bot):
    bot.add_cog(RankManagement(bot))