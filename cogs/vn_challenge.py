"""Cog for the VN challenge"""

import discord
from discord.ext import commands
import json
import boto3
import re
import asyncio
from datetime import date

#############################################################
# Variables (Temporary)
with open(f"cogs/guild_data.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]

    vn_channel_id = data_dict["vn_channel_id"]
    monthly_vn_message_id = data_dict["monthly_vn_message"]
    quarterly_vn_message_id = data_dict["quarterly_vn_message"]

    leaderboardmessage_id = data_dict["leaderboard_1"]
    leaderboardmessage2_id = data_dict["leaderboard_2"]
    leaderboardmessage3_id = data_dict["leaderboard_3"]
    leaderboardmessage4_id = data_dict["leaderboard_4"]

    # Reward roles (for voting power)
    first_checkmark_role_id = data_dict["first_checkmark_id"]
    second_checkmark_role_id = data_dict["second_checkmark_id"]
    vn_manager_id = data_dict["vn_manager_id"]
    admin_role_id = data_dict["admin_role_id"]
    # Prevent upload of files
    testing_mode = False

def is_vn_manager():
    async def predicate(ctx):
        run_command = False
        for role in ctx.author.roles:
            if role.id == vn_manager_id or role.id == admin_role_id:
                run_command = True
        return run_command
    return commands.check(predicate)

#############################################################

class VNChallenge(commands.Cog):
    """VN leaderboard and challenge"""

    def __init__(self, bot):
        self.bot = bot
        self.s3_client = boto3.client('s3')

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guild_id)
        self.vnchannel = self.bot.get_channel(vn_channel_id)
        self.monthly_vn_message = await self.vnchannel.fetch_message(monthly_vn_message_id)
        self.quarterly_vn_message = await self.vnchannel.fetch_message(quarterly_vn_message_id)

        self.leaderboardmessage = await self.vnchannel.fetch_message(leaderboardmessage_id)
        self.leaderboardmessage2 = await self.vnchannel.fetch_message(leaderboardmessage2_id)
        self.leaderboardmessage3 = await self.vnchannel.fetch_message(leaderboardmessage3_id)
        self.leaderboardmessage4 = await self.vnchannel.fetch_message(leaderboardmessage4_id)

        self.first_checkmark_role = self.myguild.get_role(first_checkmark_role_id)
        self.second_checkmark_role = self.myguild.get_role(second_checkmark_role_id)

    async def download_file(self, filename):
        self.s3_client.download_file("djtbot", f"vnchallenge/{filename}", f"data/{filename}")

        if filename.endswith('.json'):
            with open(f"data/{filename}") as json_file:
                data_dict = json.load(json_file)
        else:
            return

        return data_dict

    async def upload_file(self, data_dict, filename):

        with open(f'data/{filename}', 'w') as json_file:
            json.dump(data_dict, json_file)

        if not testing_mode:
            self.s3_client.upload_file(f"data/{filename}", "djtbot", f"vnchallenge/{filename}")
            print("Uploaded file.")

    async def update_message(self, data_dict, message, message_title):
        mymessage = [message_title]
        for index, timecode in enumerate(data_dict):
            counter = index + 1
            vn_name = data_dict[timecode][0]
            vndb_link = data_dict[timecode][1]
            code = data_dict[timecode][2]
            current_line = f"{counter}. **{timecode}** {vn_name} <{vndb_link}> Code: {code}"
            mymessage.append(current_line)

        new_message = "\n".join(mymessage)
        await message.edit(content=new_message)

    @commands.command()
    async def bingo(self, ctx):
        """VN bingo (credits to JtanK)"""
        await ctx.send(file=discord.File(r'data/images/bingo.jpg'))

    @commands.command(hidden=True)
    @is_vn_manager()
    async def addmonthlyvn(self, ctx, vn_name, vndb_link, code, year_month):
        """`<vn_name> <vndb_link> <code> <year-month>`Admin only command."""
        try:
            monthly_vn_dict = await self.download_file("monthlyvns.json")

            monthly_vn_dict[year_month] = (vn_name, vndb_link, code)

            await self.update_message(monthly_vn_dict, self.monthly_vn_message, "Past Monthly VNs:")

            await self.upload_file(monthly_vn_dict, "monthlyvns.json")

            await ctx.send(f"Added {vn_name} as {year_month} VN.")

        except discord.errors.HTTPException:
            await ctx.send("Message exceeds 2000 characters.")

    @commands.command(hidden=True)
    @is_vn_manager()
    async def addquarterlyvn(self, ctx, vn_name, vndb_link, code, year_month):
        """`<vn_name> <vndb_link> <code> <year-month-year-month>`Admin only command."""
        try:
            quarterly_vn_dict = await self.download_file("quarterlyvns.json")

            quarterly_vn_dict[year_month] = (vn_name, vndb_link, code)

            await self.update_message(quarterly_vn_dict, self.quarterly_vn_message, "Past Quarterly VNs:")

            await self.upload_file(quarterly_vn_dict, "quarterlyvns.json")

            await ctx.send(f"Added {vn_name} as {year_month} VN.")

        except discord.errors.HTTPException:
            await ctx.send("Message exceeds 2000 characters.")

    @commands.command(hidden=True)
    @is_vn_manager()
    async def removemonthlyvn(self, ctx, year_month):
        """`<year-month>`Admin only command."""
        monthly_vn_dict = await self.download_file("monthlyvns.json")

        monthly_vn_dict.pop(year_month, None)

        await self.update_message(monthly_vn_dict, self.monthly_vn_message, "Past Monthly VNs:")

        await self.upload_file(monthly_vn_dict, "monthlyvns.json")

        await ctx.send(f"Removed VN for {year_month}.")

    @commands.command(hidden=True)
    @is_vn_manager()
    async def removequarterlyvn(self, ctx, year_month):
        """`<year-month-year-month>`Admin only command."""
        quarterly_vn_dict = await self.download_file("quarterlyvns.json")

        quarterly_vn_dict.pop(year_month, None)

        await self.update_message(quarterly_vn_dict, self.quarterly_vn_message, "Past Quarterly VNs:")

        await self.upload_file(quarterly_vn_dict, "quarterlyvns.json")

        await ctx.send(f"Removed VN for {year_month}.")

    async def updateleaderboard(self, vn_challenge_dict, monthly_vn_dict, quarterly_vn_dict):
        sorted_userlist = sorted(vn_challenge_dict, key=lambda k: vn_challenge_dict[k][1], reverse=True)
        leaderboardmessage_full = ["Reading data:"]

        for index, userid in enumerate(sorted_userlist):
            userline = f"{index + 1}."
            currentpoints = vn_challenge_dict[userid][1]
            readvns = vn_challenge_dict[userid][0]
            vncodes = ""
            for readvn in readvns:
                timecode = readvn[0]
                read_in_period = readvn[1]
                if read_in_period == True:
                    if timecode in monthly_vn_dict:
                        vncode = monthly_vn_dict[timecode][2]
                    elif timecode in quarterly_vn_dict:
                        vncode = quarterly_vn_dict[timecode][2]
                    vncodes = vncodes + f" {vncode}"
                elif read_in_period == False:
                    if timecode in monthly_vn_dict:
                        vncode = monthly_vn_dict[timecode][2] + "×"
                    elif timecode in quarterly_vn_dict:
                        vncode = quarterly_vn_dict[timecode][2] + "×"
                    vncodes = vncodes + f" {vncode}"

            userline = userline + f" <@!{userid}>" + vncodes + f" {currentpoints}点"
            leaderboardmessage_full.append(userline)

        messagelist = [self.leaderboardmessage, self.leaderboardmessage2, self.leaderboardmessage3, self.leaderboardmessage4]
        counter = 0
        current_message = []
        for line in leaderboardmessage_full:
            current_message.append(line)
            short_message = "\n".join(current_message)
            if len(short_message) > 1800:
                await messagelist[counter].edit(content=short_message)
                current_message = []
                counter += 1

        await messagelist[counter].edit(content=short_message)
        return True

    async def compute_points(self, list_of_read):
        newpoints = 0
        for readpair in list_of_read:
            if readpair[1] is False and len(readpair[0]) == 7:
                newpoints += 1
            elif readpair[1] is True and len(readpair[0]) == 7:
                newpoints += 2
            elif readpair[1] is False and len(readpair[0]) == 15:
                newpoints += 2
            elif readpair[1] is True and len(readpair[0]) == 15:
                newpoints += 3

        return newpoints

    @commands.command(hidden=True)
    @is_vn_manager()
    async def clearempty(self, ctx):
        await self.clear_empty_star_roles()

    async def clear_empty_star_roles(self):
        for role in self.myguild.roles:
            if str(role).endswith("☆"):
                if len(role.members) == 0:
                    await asyncio.sleep(1)
                    await role.delete(reason="No users with role.")

    async def update_star_roles(self, vn_challenge_dict):

        for userid in vn_challenge_dict:

            current_member = self.myguild.get_member(int(userid))

            if current_member:
                current_points = int(vn_challenge_dict[userid][1])

                current_star_role = discord.utils.get(self.myguild.roles, name=f"{current_points}☆")
                if not current_star_role:
                    reference_pos_role = discord.utils.get(self.myguild.roles, name=f"1☆")
                    reference_pos = reference_pos_role.position
                    color_code = "#979c9f"
                    actual_color_code = int(re.findall(r'^#((?:[0-9a-fA-F]{3}){1,2})$', color_code)[0], base=16)
                    current_star_role = await self.myguild.create_role(name=f"{current_points}☆", colour=discord.Colour(actual_color_code))
                    positions = {current_star_role: reference_pos - 1}
                    await self.myguild.edit_role_positions(positions)

                has_role = False
                for role in current_member.roles:
                    if str(role).endswith("☆"):
                        if role == current_star_role:
                            has_role = True
                        else:
                            await asyncio.sleep(1)
                            await current_member.remove_roles(role)
                            await asyncio.sleep(1)
                            await current_member.add_roles(current_star_role)
                            has_role = True

                if not has_role:
                    await asyncio.sleep(1)
                    await current_member.add_roles(current_star_role)

                if current_points >= 7:
                    if self.second_checkmark_role not in current_member.roles:
                        await asyncio.sleep(1)
                        await current_member.add_roles(self.second_checkmark_role)
                    if self.first_checkmark_role in current_member.roles:
                        await asyncio.sleep(1)
                        await current_member.remove_roles(self.first_checkmark_role)
                elif current_points < 7:
                    if self.first_checkmark_role not in current_member.roles:
                        await asyncio.sleep(1)
                        await current_member.add_roles(self.first_checkmark_role)
                    if self.second_checkmark_role in current_member.roles:
                        await asyncio.sleep(1)
                        await current_member.remove_roles(self.second_checkmark_role)

        await self.clear_empty_star_roles()
        return True

    @commands.command(hidden=True)
    @is_vn_manager()
    async def addvn(self, ctx, mention, *vncodes):
        vn_challenge_dict = await self.download_file("vnchallenge.json")
        monthly_vn_dict = await self.download_file("monthlyvns.json")
        quarterly_vn_dict = await self.download_file("quarterlyvns.json")

        current_date = str(date.today())[0:7]
        mentionid = re.findall(r"(\d+)", mention)[0]

        try:
            previous_points = vn_challenge_dict[mentionid][1]
            read_vns = vn_challenge_dict[mentionid][0]
        except KeyError:
            previous_points = 0
            read_vns = []

        vntitles = []
        for vncode in vncodes:
            for datecode in monthly_vn_dict:
                if vncode == monthly_vn_dict[datecode][2]:
                    if datecode == current_date:
                        vntoadd = [datecode, True]
                        read_vns.append(vntoadd)
                        vntitles.append(monthly_vn_dict[datecode][0])
                    else:
                        vntoadd = [datecode, False]
                        read_vns.append(vntoadd)
                        vntitles.append(monthly_vn_dict[datecode][0])

            for datecode in quarterly_vn_dict:
                if vncode == quarterly_vn_dict[datecode][2]:
                    begining_period = datecode[0:7]
                    end_period = datecode[8:15]

                    def nextmonth(shortMonth):
                        return {'01': "02",
                                '02': "03",
                                '03': "04",
                                '04': "05",
                                '05': "06",
                                '06': "07",
                                '07': "08",
                                '08': "09",
                                '09': "10",
                                '10': "11",
                                '11': "12",
                                '12': "01"}[shortMonth]

                    next_month = nextmonth(datecode[5:7])
                    if next_month == "01":
                        next_year = str((int(datecode[0:4]) + 1))
                    else:
                        next_year = datecode[0:4]

                    inter_period = f"{next_year}-{next_month}"
                    periods = [begining_period, inter_period, end_period]

                    if current_date in periods:
                        vntoadd = [datecode, True]
                        read_vns.append(vntoadd)
                        vntitles.append(quarterly_vn_dict[datecode][0])
                    else:
                        vntoadd = [datecode, False]
                        read_vns.append(vntoadd)
                        vntitles.append(quarterly_vn_dict[datecode][0])

        rewards_vns_string = ", ".join(vntitles)
        newpoints = await self.compute_points(read_vns)
        vn_challenge_dict[mentionid] = [read_vns, newpoints]

        await self.upload_file(vn_challenge_dict, "vnchallenge.json")
        await ctx.send(f"Rewarded **{rewards_vns_string}** to <@!{mentionid}>; {previous_points} -> {newpoints} Points")

        if await self.update_star_roles(vn_challenge_dict) == True:
            await ctx.send("Updated star roles.")

        if await self.updateleaderboard(vn_challenge_dict, monthly_vn_dict, quarterly_vn_dict) == True:
            await ctx.send("Updated leaderboard.")

    @commands.command(hidden=True)
    @is_vn_manager()
    async def removevn(self, ctx, mention, *vncodes):
        vn_challenge_dict = await self.download_file("vnchallenge.json")
        monthly_vn_dict = await self.download_file("monthlyvns.json")
        quarterly_vn_dict = await self.download_file("quarterlyvns.json")

        mentionid = re.findall(r"(\d+)", mention)[0]
        previous_points = vn_challenge_dict[mentionid][1]
        read_vns = vn_challenge_dict[mentionid][0]
        vntitles = []

        for vncode in vncodes:
            for datecode in monthly_vn_dict:
                if vncode == monthly_vn_dict[datecode][2]:
                    for readdata in read_vns:
                        if readdata[0] == datecode:
                            read_vns.remove(readdata)
                            vntitles.append(monthly_vn_dict[datecode][0])

            for datecode in quarterly_vn_dict:
                if vncode == quarterly_vn_dict[datecode][2]:
                    for readdata in read_vns:
                        if readdata[0] == datecode:
                            read_vns.remove(readdata)
                            vntitles.append(quarterly_vn_dict[datecode][0])

        rewards_vns_string = ", ".join(vntitles)
        newpoints = await self.compute_points(read_vns)

        vn_challenge_dict[mentionid] = [read_vns, newpoints]

        if len(read_vns) == 0:
            del vn_challenge_dict[mentionid]

        await ctx.send(
            f"Removed **{rewards_vns_string}** from <@!{mentionid}>; {previous_points} -> {newpoints} Points")

        await self.upload_file(vn_challenge_dict, "vnchallenge.json")

        if await self.update_star_roles(vn_challenge_dict) == True:
            await ctx.send("Updated star roles.")

        if await self.updateleaderboard(vn_challenge_dict, monthly_vn_dict, quarterly_vn_dict) == True:
            await ctx.send("Updated leaderboard.")

    @commands.command(hidden=True)
    @is_vn_manager()
    async def updatevn(self, ctx):
        vn_challenge_dict = await self.download_file("vnchallenge.json")
        monthly_vn_dict = await self.download_file("monthlyvns.json")
        quarterly_vn_dict = await self.download_file("quarterlyvns.json")

        if await self.update_star_roles(vn_challenge_dict) == True:
            await ctx.send("Updated star roles.")

        if await self.updateleaderboard(vn_challenge_dict, monthly_vn_dict, quarterly_vn_dict) == True:
            await ctx.send("Updated leaderboard.")
        try:
            await self.update_message(monthly_vn_dict, self.monthly_vn_message, "Past Monthly VNs:")
            await self.update_message(quarterly_vn_dict, self.quarterly_vn_message, "Past Quarterly VNs:")

        except discord.errors.HTTPException:
            await ctx.send("Message exceeds 2000 characters.")

def setup(bot):
    bot.add_cog(VNChallenge(bot))