"""Cog responsible for the level-up rank system."""

import json
import random
import re
import discord
import time
import aiohttp
from discord.ext import commands

#############################################################
# Variables (Temporary)
with open(f"cogs/guild_data.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]
    kotobabotid = data_dict["kotoba_id"]
    join_quiz_channel_ids = [data_dict["join_quiz_1_id"], data_dict["join_quiz_2_id"]]
    announcement_channel_id = data_dict["otaku_channel_id"]
    quizranks = data_dict["quizranks"]
    mycommands = data_dict["mycommands"]
    mycommands = {int(key): value for key, value in mycommands.items()}
    myrankstructure = data_dict["rank_structure"]
#############################################################

class Quiz(commands.Cog):
    """Commands in relation to the Quiz."""

    def __init__(self, bot):
        self.bot = bot

    async def getjson(self, url):
        async with self.aiosession.get(url) as resp:
            return await resp.json()

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guild_id)
        self.aiosession = aiohttp.ClientSession()

    @commands.command()
    async def ranktable(self, ctx):
        """
        Get the quiz rank of all server members.
        """
        # Additionally makes sure all members are accounted for and nobody is missing a role.
        membercountdict = dict()
        membercount = 0
        accountedfor = 0
        emptyusers = []
        for member in self.myguild.members:
            emptyusers.append(str(member))
            membercount += 1

            if member.bot:
                accountedfor += 1
                emptyusers.remove(str(member))

            for role in member.roles:
                if role.id in quizranks:
                    try:
                        emptyusers.remove(str(member))
                    except ValueError:
                        await ctx.send(f"Found user with duplicate role: {member.mention}")
                    accountedfor += 1
                    membercountdict[role.id] = membercountdict.get(role.id, 0) + 1

        message = "Role distribution:\n"
        for roleid in quizranks:
            message += f"{self.myguild.get_role(roleid)}: {membercountdict[roleid]}\n"
        message += f"Total members: {membercount} ({accountedfor} accounted for)."

        await ctx.send(message)

    @commands.command()
    async def levelup(self, ctx):
        """
        Get your next levelup command (per PM).
        """
        member = await self.myguild.fetch_member(ctx.author.id)
        for role in member.roles:
            if role.id in quizranks:
                # String is cut down for easy copy and paste.
                currentcommand = re.search(r"`(.*)`", mycommands[role.id]).group(1)

        await ctx.author.create_dm()
        private_channel = ctx.author.dm_channel

        await private_channel.send(currentcommand)
        await private_channel.send(
            f"Use this command for your next level-up.\nTo see all quiz commands type `$levelupall`")

    @commands.command()
    async def levelupall(self, ctx):
        """
        Get all levelup commands (per PM).
        """
        message_list = []
        message_list.append("Type `$help` to get a list of all commands.\n")

        for rankid in mycommands:
            levelupmesssage = mycommands[rankid]
            message_list.append(levelupmesssage)

        # Delete final level message.
        del message_list[-1]

        message = "\n".join(message_list)

        await ctx.author.create_dm()
        private_channel = ctx.author.dm_channel
        await private_channel.send(message)

    @commands.command()
    async def rankusers(self, ctx, *, rolename):
        """
        `<rolename>` Get a name list of users with the specified role.
        """
        try:
            for role in self.myguild.roles:
                if role.name == rolename:
                    desired_role = role

            userlist = []
            for member in self.myguild.members:
                for role in member.roles:
                    if role == desired_role:
                        userlist.append(str(member))

            message = f"The following {len(userlist)} users have the role **{desired_role.name}**:\n"
            userstring = "\n".join(userlist)

            await ctx.send(message + userstring)

        except discord.errors.HTTPException:
            await ctx.send("Message longer than 2000 characters. Sending per PM.")
            await ctx.author.create_dm()
            private_channel = ctx.author.dm_channel

            await private_channel.send(f"The following {len(userlist)} users have the role **{desired_role.name}**:\n")

            short_userstring = []
            usernames = userstring.splitlines()

            for index, name in enumerate(usernames):
                short_userstring.append(name)
                usernames.remove(name)
                short_message = "\n".join(short_userstring)
                if len(short_message) > 1800:
                    await private_channel.send(short_message)
                    short_userstring = []
            await private_channel.send(short_message)

    # Quiz reward function.
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id == kotobabotid:
            kotobaembeds = message.embeds
            try:
                if kotobaembeds:
                    for embed in kotobaembeds:
                        fields = embed.fields
                        if 'Ended' in embed.title:
                            for field in fields:
                                if "[View a report for this game]" in field.value:
                                    quizid = re.search(r'game_reports/([^)]*)\)', field.value).group(1)
                                    jsonurl = f"https://kotobaweb.com/api/game_reports/{quizid}"


                                    print("Download kotobabot json.")
                                    start = time.time()
                                    kotobadict = await self.getjson(jsonurl)
                                    end = time.time()
                                    print(f"Finished downloading kotoba json with runtime: {end - start} seconds")

                                    usercount = len(kotobadict["participants"])
                                    questioncount = len(kotobadict["questions"])
                                    mainuserid = int(kotobadict["participants"][0]["discordUser"]["id"])
                                    scorelimit = kotobadict["settings"]["scoreLimit"]
                                    failedquestioncount = questioncount - scorelimit
                                    answertimelimitinms = kotobadict["settings"]["answerTimeLimitInMs"]
                                    fontsize = kotobadict["settings"]["fontSize"]
                                    font = kotobadict["settings"]["font"]
                                    shuffle = kotobadict["settings"]["shuffle"]
                                    isloaded = kotobadict["isLoaded"]
                                    myscore = kotobadict["scores"][0]["score"]

                                    # Multideck quiz
                                    if len(kotobadict["decks"]) == 1:
                                        quizname = kotobadict["sessionName"]
                                    else:
                                        quizname = ""
                                        for deckdict in kotobadict["decks"]:
                                            addname = deckdict["name"]
                                            quizname += " " + addname

                                    startindex = 0
                                    endindex = 0

                                    mc = kotobadict["decks"][0]["mc"]

                                    try:
                                        startindex = kotobadict["decks"][0]["startIndex"]
                                        endindex = kotobadict["decks"][0]["endIndex"]

                                    except KeyError:
                                        pass

                                    try:
                                        requirements = myrankstructure[quizname]
                                        reqscorelimit, reqanswertime, reqfontsize, reqfont, newrankid, reqfailed = requirements
                                    except KeyError:
                                        if message.channel.id in join_quiz_channel_ids:
                                            await message.channel.send("Not a ranked quiz. Use the following command:")
                                            await message.channel.send(
                                                f"{re.search(r'`(.*)`', mycommands[list(mycommands.keys())[0]]).group(1)}")
                                        print("Not a ranked quiz.")
                                        return

                                    if startindex != 0 or endindex != 0 or mc == True or shuffle == False or isloaded == True:
                                        if message.channel.id in join_quiz_channel_ids:
                                            await message.channel.send(
                                                "Cheat settings detected. Use the following command:")
                                            await message.channel.send(
                                                f"{re.search(r'`(.*)`', mycommands[list(mycommands.keys())[0]]).group(1)}")
                                        print("Cheat settings detected.")
                                        return

                                    if scorelimit != myscore:
                                        if message.channel.id in join_quiz_channel_ids:
                                            await message.channel.send(
                                                "Failed quiz. Use the following command to try again:")
                                            await message.channel.send(
                                                f"{re.search(r'`(.*)`', mycommands[list(mycommands.keys())[0]]).group(1)}")
                                        print("Score and limit don't match.")
                                        return

                                    if scorelimit < reqscorelimit:
                                        if message.channel.id in join_quiz_channel_ids:
                                            await message.channel.send("Score too low. Use the following command:")
                                            await message.channel.send(
                                                f"{re.search(r'`(.*)`', mycommands[list(mycommands.keys())[0]]).group(1)}")
                                        print("Score too low.")
                                        return

                                    if usercount > 1:
                                        if message.channel.id in join_quiz_channel_ids:
                                            await message.channel.send(
                                                "Too many users. Do the quiz alone and use the following command:")
                                            await message.channel.send(
                                                f"{re.search(r'`(.*)`', mycommands[list(mycommands.keys())[0]]).group(1)}")
                                        print("Too many users.")
                                        return

                                    if reqanswertime < answertimelimitinms:
                                        if message.channel.id in join_quiz_channel_ids:
                                            await message.channel.send(
                                                "Answer time too long. Use the following command:")
                                            await message.channel.send(
                                                f"{re.search(r'`(.*)`', mycommands[list(mycommands.keys())[0]]).group(1)}")
                                        print("Answer time too long.")
                                        return

                                    if reqfontsize < fontsize:
                                        if message.channel.id in join_quiz_channel_ids:
                                            await message.channel.send("Font size too big. Use the following command:")
                                            await message.channel.send(
                                                f"{re.search(r'`(.*)`', mycommands[list(mycommands.keys())[0]]).group(1)}")
                                        print("Font size too big.")
                                        return

                                    if reqfont != 'any':
                                        if font != reqfont:
                                            if message.channel.id in join_quiz_channel_ids:
                                                await message.channel.send(
                                                    "Font not correct. Use the following command:")
                                                await message.channel.send(
                                                    f"{re.search(r'`(.*)`', mycommands[list(mycommands.keys())[0]]).group(1)}")

                                            print("Font not correct.")
                                            return

                                    if failedquestioncount < 0:
                                        if message.channel.id in join_quiz_channel_ids:
                                            await message.channel.send("Quiz aborted. Use the following command:")
                                            await message.channel.send(
                                                f"{re.search(r'`(.*)`', mycommands[list(mycommands.keys())[0]]).group(1)}")
                                        print("Negative fails (Quiz aborted).")
                                        return

                                    if failedquestioncount > reqfailed:
                                        if message.channel.id in join_quiz_channel_ids:
                                            await message.channel.send("Too many failed. Use the following command:")
                                            await message.channel.send(
                                                f"{re.search(r'`(.*)`', mycommands[list(mycommands.keys())[0]]).group(1)}")
                                        print("Too many failed.")
                                        return

                                    quizwinner = self.myguild.get_member(mainuserid)
                                    for role in quizwinner.roles:
                                        if role.id in quizranks:
                                            print("Role ID:", role.id)
                                            currentroleid = role.id

                                    if quizranks.index(currentroleid) == quizranks.index(newrankid) - 1:
                                        currentrole = self.myguild.get_role(currentroleid)
                                        newrole = self.myguild.get_role(newrankid)
                                        await quizwinner.remove_roles(currentrole)
                                        await quizwinner.add_roles(newrole)
                                        announcementchannel = self.bot.get_channel(announcement_channel_id)
                                        await announcementchannel.send(f'<@!{mainuserid}> has passed the {quizname}!\n'
                                                                       f'Type `$levelup` to get the next level-up command.')

            except TypeError:
                pass

    @commands.command()
    async def generatequiz(self, ctx):
        "Generates a semi-random quiz."
        basis = "k!quiz"
        quiz_selection = ['N3', 'N2', 'N1', 'suugaku', 'pasokon', 'rikagaku', 'igaku',
                          'shinrigaku', 'keizai', 'houritsu', 'kenchiku', 'buddha', 'nature', 'animals', 'birds',
                          'bugs', 'fish', 'plants', 'vegetables', 'tokyo', 'places_full', 'rtk_vocab', 'common',
                          'common_nojlpt', 'k33', 'hard', 'haard', 'insane', 'ranobe', 'numbers', 'yojijukugo',
                          'myouji', 'namae', 'cope', 'jpdefs', 'jpdefs', 'jouyou']

        my_quiz_length = random.randint(2, 5)
        my_quizzes = ""
        for i in range(my_quiz_length):
            if i == 0:
                my_quizzes = quiz_selection[random.randint(0, 36)]
            else:
                my_quizzes = my_quizzes + "+" + quiz_selection[random.randint(0, 36)]

        score_limit = random.randint(10, 20)

        pacers = ["nodelay", "faster", "fast", ""]
        mypacing = pacers[random.randint(0, 3)]

        answer_time = random.randint(7, 14)
        atl = f"atl={answer_time}"

        additional_answer_wait = random.randint(0, 3)
        aaww = f"aaww={additional_answer_wait}"

        dauq = "dauq=1"
        daaq = "daaq=1"

        font_list = [1, 3, 4, 5, 7, 9, 10, 13, 15, 24]
        myfont = f"font={font_list[random.randint(0, 9)]}"

        message = f"{basis} {my_quizzes} {atl} {aaww} {dauq} {daaq} {myfont} {score_limit} {mypacing}"
        await ctx.send(message)

def setup(bot):
    bot.add_cog(Quiz(bot))
