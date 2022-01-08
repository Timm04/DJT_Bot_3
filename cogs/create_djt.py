"""This cog contains functions to recreate the entirety of the Japanese Thread Discord from scratch und register
all IDs to the guild_data.json file, enabling other cogs to work with the data. The following is restored by this cog:
- Channel structure, names, descriptions and permissions.
- Role structure, names and permissions.
- Settings for the level up system.
- A selected amount of emojis for up to Discord booster level 2.
- Selected important messages:
    - VN and Disboard leaderboards.
    - Role selection message.
    - The join welcome message.
    - Message detailing threads.
    - Message for beginners of Japanese.

Additional features:
- Checks if important bots are present (to restore their permissions).
- Sync roles from rolesdata.json to the backup guild.
- Download all emoji in the guild defined by the command context."""

import discord
from discord.ext import commands
from discord.ext import tasks
import asyncio
import json
import boto3
import os

djt_channels = {
    "GENERAL": [("otaku", "Japanese language and otaku media related chat."),
                ("elite-otaku", "少数精鋭"),
                ("nihongo", "Chat in Japanese"),
                ("offtopic", "real life, blogposts, travel, and others"),
                ("artwork", "Wholesome SFW Artwork only."),
                ("vn", "VN of the Month: To talk in this channel react to the relevant message in #welcome. Check "
                       "pins for ongoing votes and the leaderboard."),
                ("books", "Japanese books and group reads. | To write here react to the message in #welcome."),
                ("manga", "Channel for the manga club."),
                ("djt-radio", "Post or talk about music."),
                ("public-apology", "Channel in which punished users can ask for forgiveness.")],

    "OTHER": [("quiz", "k!quiz <quiz>"),
              ("quiz-solo", "Please don't interfere with other people doing the quiz."),
              ("quiz-solo2", "Please don't interfere with other people doing the quiz."),
              ("bump", "!d bump"),
              ("vc-chat", "Voice chat text channel.")],

    "JOIN": [("welcome", "Welcome to DJT Discord!"),
             ("beginner-questions", "Read the pinned messages if you're a beginner."),
             ("search-request", "Search for anime scenes."),
             ("join-quiz", "Please read the pinned message to find out how to join."),
             ("join-quiz2", "Please read the pinned message to find out how to join."),
             ("mod", "Moderator channel."),
             ("elite-mod", "$clear to empty channel. | Messages in this channel are cleared automatically after 24h.")]
}
voice_channels = {
    "OTHER": ["free-talk 64kbps", "free-talk 256kbps"]
}

bot_ids = {
    "Kotoba": 251239170058616833,
    "Pollmaster": 444514223075360800,
    "Dyno": 155149108183695360,
    "Disboard": 302050872383242240
}

user_ids = {
    "QM": 659876763652063282,
    "nullposter": 182138235206631434
}

backup_server_id = 862488397371932672

join_quiz_pinned_message = """Welcome to Daily Japanese Thread. Access to all channels is restricted to Japanese learners!
To join type `k!quiz n4 nodelay atl=10 14 size=80 mmq=2` and get 14 points (max 1 failed question).
You have unlimited tries. More Information in welcome

DJT Chatへようこそ
このサーバーは日本語検定でN4級以上の日本語力がある方にのみ入室が許可されています。
`k!quiz n4 nodelay atl=10 14 size=80 mmq=2`と入力し、日本語のテストを開始してください。
合格点は14点、ミスは2回までです。何回でもチャレンジしてください。 
"""

role_perks_message = """Role perks:\n
N4: 
- Access to the main chat and event roles
N3: 
- Access to the VN channel and VN challenge
N2:
- Talk in the beginner questions room
N1:
- Access to the elite otaku room
Taikou:
- Create a custom role with a custom color
Daiou: 
- Access to emoji management through bot (up to 5 per user)
- View the hidden mod channel

Server Boosters:
- All of the above (except server access and mod channel) and custom role image"""

reactions_string = """React to this message to get the corresponding role.

🖋️ : Visual novel reading challenge and access to the VN channel..
📖 : Book club and access to the book channel.
🥭 : Manga club and access to the manga channel.
📹 : Mentionable role for group reading events.
💬 : Mentionable role for having Japanese conversations.
🎥 : Role for the movie evenings.
❗ : Role to get notifications when a bump is due in the bump channel.
⭐ : Role for general purpose events such as karaoke, challenges or competitions."""
reaction_emojis = ['🖋️', '📖', '🥭', '📹', '💬', '🎥', '❗', '⭐']

invite_link_message = """Invite link always here: https://animecards.site/discord/ (bookmark it)

Most recent backup link always here:
https://animecards.site/discord_backup/ 
"""

threads_message = """Currently Active General Threads Overview. All threads can be revived by any user.

Seasonal Anime 
Talk about current airing shows.

Mining 
Talk about interesting and rare words that you added to Anki.

Kanken Practice 
Talk about the kanji writing, the Kanji Kentei test, the Kanken Anki deck and other related topics.

Bible Study
Reading and discussing the bible. Each week another book.

Daily Accountability Thread 
Talk about commitments and plans and stick to them.

Linux & Programming 
Talk about alternative operating systems and programming.

Currently Archived:

Pitch Practice
Talk about Japanese pitch accent and learning it.

vc-chat2 
Second voice channel in case of parallel discussion."""

beginner_message = """If you are a beginner follow this guide by QM (and the rest of the website):
＞＞ <https://animecards.site/learningjapanese/> ＜＜
tl;dr
・start consuming native japanese content <https://rentry.co/japanese_resources>
・do core 2.3k <https://anacreondjt.gitlab.io/docs/coredeck/>
・skim through tae kim <https://itazuraneko.neocities.org/grammar/taekim.html>

Other resources can be found on my site <https://anacreondjt.gitlab.io/> 
and on the tmw's resource page <https://rentry.co/japanese_resources>
stegatxins0 wrote a really in-depth advanced anki mining guide that more advanced learner's may find helpful <https://rentry.co/mining>"""

bot_role_name = "幽人の庭師"


class Restoration(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.loop_iteration = 0
        self.s3_client = boto3.client('s3')

    @commands.Cog.listener()
    async def on_ready(self):
        pass
        # self.sync_roles_new.start()

    @commands.command(hidden=True)
    @commands.is_owner()
    async def check_for_bots(self, ctx):
        "Check if all important bots are members of the guild."

        on_server_bot_ids = [member.id for member in ctx.guild.members if member.bot is True]

        for bot_name in bot_ids:
            if bot_ids[bot_name] not in on_server_bot_ids:
                await asyncio.sleep(1)
                await ctx.send(f"Please add the {bot_name} bot to the server.")
                return False

        return True

    @commands.command(hidden=True)
    @commands.is_owner()
    async def create_channels(self, ctx):
        "Delete all channels except 'revive' and recreate them in accordance with the djt_channels variable."

        for channel in ctx.guild.channels:
            if not channel.name == "revive":
                await asyncio.sleep(1)
                await channel.delete()
        await ctx.send("Deleted old channels.")

        for category in djt_channels:
            await asyncio.sleep(1)
            current_category = await ctx.guild.create_category(category)
            for channel in djt_channels[category]:
                await asyncio.sleep(1)
                await ctx.guild.create_text_channel(channel[0], category=current_category, topic=channel[1])

            if category in voice_channels:
                for channel in voice_channels[category]:
                    await asyncio.sleep(1)
                    await ctx.guild.create_voice_channel(channel, category=current_category)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def create_roles(self, ctx):
        """Delete old roles and recreate all standard roles."""

        roles_to_delete = [role for role in ctx.guild.roles if
                           not role.is_default() and not role.is_premium_subscriber() and not role.is_bot_managed()]
        for role in roles_to_delete:
            await asyncio.sleep(1)
            await role.delete()
        await ctx.send("Old roles deleted.")

        djt_roles = {
            "Admin": discord.Colour.default(),
            "Mod": discord.Colour.default(),
            "Muted": discord.Colour.dark_grey(),
            "Pos. Reference Role": discord.Colour.default(),
            "日本人": discord.Colour.gold(),
            "大王": discord.Colour(int("990505", base=16)),
            "大公": discord.Colour(int("bc002d", base=16)),
            "公爵": discord.Colour.red(),
            "侯爵": discord.Colour.orange(),
            "伯爵 / N3": discord.Colour.blue(),
            "子爵 / N4": discord.Colour.teal(),
            "農奴 / Unranked": discord.Colour.default(),
            "VN Challenge": discord.Colour(int("c2aaaa", base=16)),
            "VN Manager": discord.Colour(int("c2aaaa", base=16)),
            "Book Club": discord.Colour.purple(),
            "Reading Stream": discord.Colour.dark_green(),
            "Manga Club": discord.Colour.dark_purple(),
            "Movie": discord.Colour.green(),
            "Conversation": discord.Colour.dark_teal(),
            "Bumper": discord.Colour.teal(),
            "Quiz God": discord.Colour.dark_purple(),
            "Quizzer": discord.Colour.dark_purple(),
            "Student": discord.Colour.dark_purple(),
            "Supporter": discord.Colour.dark_purple(),
            "Polluser": discord.Colour.default(),
            "Emoji": discord.Colour.default(),
            "Event": discord.Colour.dark_orange(),
            "✓": discord.Colour.default(),
            "✓✓": discord.Colour.default(),
            "1☆": discord.Colour.default()
        }

        for role_name in djt_roles:
            await asyncio.sleep(1)
            await ctx.guild.create_role(name=role_name, colour=djt_roles[role_name])

    @commands.command(hidden=True)
    @commands.is_owner()
    async def update_role_and_channel_permissions(self, ctx):
        """Update permissions for roles and channels."""
        admin_role = discord.utils.get(ctx.guild.roles, name='Admin')
        mod_role = discord.utils.get(ctx.guild.roles, name='Mod')
        n4_role = discord.utils.get(ctx.guild.roles, name='子爵 / N4')
        n3_role = discord.utils.get(ctx.guild.roles, name='伯爵 / N3')
        n2_role = discord.utils.get(ctx.guild.roles, name='侯爵')
        n1_role = discord.utils.get(ctx.guild.roles, name='公爵')
        taikou_role = discord.utils.get(ctx.guild.roles, name='大公')
        daiou_role = discord.utils.get(ctx.guild.roles, name='大王')
        unranked_role = discord.utils.get(ctx.guild.roles, name='農奴 / Unranked')
        everyone_role = discord.utils.get(ctx.guild.roles, name='@everyone')
        muted_role = discord.utils.get(ctx.guild.roles, name='Muted')
        vn_role = discord.utils.get(ctx.guild.roles, name='VN Challenge')
        manga_role = discord.utils.get(ctx.guild.roles, name='Manga Club')
        book_role = discord.utils.get(ctx.guild.roles, name='Book Club')
        student_role = discord.utils.get(ctx.guild.roles, name='Student')
        quizzer_role = discord.utils.get(ctx.guild.roles, name='Quizzer')
        quiz_god_role = discord.utils.get(ctx.guild.roles, name='Quiz God')
        kotoba_role = discord.utils.get(ctx.guild.roles, name='Kotoba')
        disboard_role = discord.utils.get(ctx.guild.roles, name='DISBOARD.org')

        await unranked_role.edit(hoist=True)
        await asyncio.sleep(1)
        await n4_role.edit(hoist=True)
        await asyncio.sleep(1)
        await n3_role.edit(hoist=True)
        await asyncio.sleep(1)
        await n2_role.edit(hoist=True)
        await asyncio.sleep(1)
        await n1_role.edit(hoist=True)
        await asyncio.sleep(1)
        await taikou_role.edit(hoist=True)
        await asyncio.sleep(1)
        await daiou_role.edit(hoist=True)
        await asyncio.sleep(1)

        bot_role = discord.utils.get(ctx.guild.roles, name=bot_role_name)
        await admin_role.edit(permissions=discord.Permissions(permissions=8), reason="Give admin rights to admin role.",
                              position=bot_role.position - 1)
        await asyncio.sleep(1)
        await mod_role.edit(permissions=discord.Permissions(permissions=1237328006),
                            reason="Give mod rights to mod role.")
        await asyncio.sleep(1)
        await everyone_role.edit(permissions=discord.Permissions(permissions=70635201), reason="Set default role.")
        await asyncio.sleep(1)

        qm = await ctx.guild.fetch_member(user_ids["QM"])
        await qm.add_roles(admin_role)

        general_category = discord.utils.get(ctx.guild.channels, name='GENERAL')
        await general_category.set_permissions(unranked_role, read_messages=False)
        await asyncio.sleep(1)
        await general_category.set_permissions(muted_role, send_messages=False, add_reactions=False)
        await asyncio.sleep(1)
        await general_category.set_permissions(student_role, read_messages=True)
        await asyncio.sleep(1)
        await general_category.set_permissions(quizzer_role, read_messages=True)
        await asyncio.sleep(1)
        await general_category.set_permissions(quiz_god_role, read_messages=True)
        await asyncio.sleep(1)
        await general_category.set_permissions(kotoba_role, send_messages=False, add_reactions=False)
        await asyncio.sleep(1)
        await general_category.set_permissions(disboard_role, send_messages=False, add_reactions=False)
        await asyncio.sleep(1)

        other_category = discord.utils.get(ctx.guild.channels, name='OTHER')
        await other_category.set_permissions(unranked_role, read_messages=False)
        await asyncio.sleep(1)
        await other_category.set_permissions(muted_role, send_messages=False, add_reactions=False)
        await asyncio.sleep(1)
        await other_category.set_permissions(student_role, read_messages=True)
        await asyncio.sleep(1)
        await other_category.set_permissions(quizzer_role, read_messages=True)
        await asyncio.sleep(1)
        await other_category.set_permissions(quiz_god_role, read_messages=True)
        await asyncio.sleep(1)

        join_category = discord.utils.get(ctx.guild.channels, name='JOIN')
        await join_category.set_permissions(muted_role, send_messages=False, add_reactions=False)
        await asyncio.sleep(1)

        elite_channel = discord.utils.get(ctx.guild.channels, name='elite-otaku')
        await elite_channel.set_permissions(everyone_role, read_messages=False)
        await asyncio.sleep(1)
        await elite_channel.set_permissions(n1_role, read_messages=True)
        await asyncio.sleep(1)
        await elite_channel.set_permissions(taikou_role, read_messages=True)
        await asyncio.sleep(1)
        await elite_channel.set_permissions(daiou_role, read_messages=True)
        await asyncio.sleep(1)

        vn_channel = discord.utils.get(ctx.guild.channels, name='vn')
        await vn_channel.set_permissions(everyone_role, send_messages=False)
        await asyncio.sleep(1)
        await vn_channel.set_permissions(vn_role, send_messages=True)
        await asyncio.sleep(1)

        manga_channel = discord.utils.get(ctx.guild.channels, name='manga')
        await manga_channel.set_permissions(everyone_role, send_messages=False)
        await asyncio.sleep(1)
        await manga_channel.set_permissions(manga_role, send_messages=True)
        await asyncio.sleep(1)

        books_channel = discord.utils.get(ctx.guild.channels, name='books')
        await books_channel.set_permissions(everyone_role, send_messages=False)
        await asyncio.sleep(1)
        await books_channel.set_permissions(book_role, send_messages=True)
        await asyncio.sleep(1)

        apology_channel = discord.utils.get(ctx.guild.channels, name='public-apology')
        await apology_channel.set_permissions(everyone_role, send_messages=False)
        await asyncio.sleep(1)
        await apology_channel.set_permissions(muted_role, send_messages=True)
        await asyncio.sleep(1)

        welcome_channel = discord.utils.get(ctx.guild.channels, name='welcome')
        await welcome_channel.set_permissions(everyone_role, send_messages=False)
        await asyncio.sleep(1)

        beginner_questions_channel = discord.utils.get(ctx.guild.channels, name='beginner-questions')
        await beginner_questions_channel.set_permissions(n3_role, send_messages=False)
        await asyncio.sleep(1)
        await beginner_questions_channel.set_permissions(n4_role, send_messages=False)
        await asyncio.sleep(1)

        join_quiz_1_channel = discord.utils.get(ctx.guild.channels, name='join-quiz')
        await join_quiz_1_channel.set_permissions(everyone_role, send_messages=False)
        await asyncio.sleep(1)
        await join_quiz_1_channel.set_permissions(unranked_role, send_messages=True)
        await asyncio.sleep(1)
        await join_quiz_1_channel.set_permissions(kotoba_role, send_messages=True)
        await asyncio.sleep(1)
        join_quiz_2_channel = discord.utils.get(ctx.guild.channels, name='join-quiz2')
        await join_quiz_2_channel.set_permissions(everyone_role, send_messages=False)
        await asyncio.sleep(1)
        await join_quiz_2_channel.set_permissions(unranked_role, send_messages=True)
        await asyncio.sleep(1)
        await join_quiz_2_channel.set_permissions(kotoba_role, send_messages=True)
        await asyncio.sleep(1)

        mod_channel = discord.utils.get(ctx.guild.channels, name='mod')
        await mod_channel.set_permissions(everyone_role, read_messages=False)
        await asyncio.sleep(1)
        await mod_channel.set_permissions(mod_role, read_messages=True)
        await asyncio.sleep(1)
        await mod_channel.set_permissions(daiou_role, read_messages=True)
        await asyncio.sleep(1)

        elite_mod_channel = discord.utils.get(ctx.guild.channels, name='elite-mod')
        await elite_mod_channel.set_permissions(everyone_role, read_messages=False)
        await asyncio.sleep(1)
        await elite_mod_channel.set_permissions(mod_role, read_messages=True)
        await asyncio.sleep(1)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def readd_emoji_list(self, ctx):
        """Delete all old emojis and readd them from the emoji folders (corresponding to booster levels)."""

        for emoji in ctx.guild.emojis:
            await asyncio.sleep(1)
            await emoji.delete()

        await ctx.send("Deleted old emoji.")

        emoji_count = 0

        emoji_directories = ["data/emojis/level_0/", "data/emojis/level_1/", "data/emojis/level_2/"]
        for directory in emoji_directories:
            for filename in os.listdir(directory):
                with open(f"{directory + filename}", 'rb') as emoji_file:
                    emoji_image = emoji_file.read()
                    await ctx.guild.create_custom_emoji(name=filename, image=emoji_image)
                    emoji_count += 1

                if emoji_count >= ctx.guild.emoji_limit:
                    await ctx.send("Added maximum amount of emojis. Exiting.")
                    return

    @commands.command(hidden=True)
    @commands.is_owner()
    async def create_messages(self, ctx):

        join_quiz_1_channel = discord.utils.get(ctx.guild.channels, name='join-quiz')
        message = await join_quiz_1_channel.send(join_quiz_pinned_message)
        await asyncio.sleep(1)
        await message.pin()
        await asyncio.sleep(1)

        join_quiz_2_channel = discord.utils.get(ctx.guild.channels, name='join-quiz2')
        message = await join_quiz_2_channel.send(join_quiz_pinned_message)
        await asyncio.sleep(1)
        await message.pin()
        await asyncio.sleep(1)

        otaku_channel = discord.utils.get(ctx.guild.channels, name='otaku')
        message = await otaku_channel.send(role_perks_message)
        await asyncio.sleep(1)
        await message.pin()
        await asyncio.sleep(1)

        message = await otaku_channel.send(threads_message)
        await asyncio.sleep(1)
        await message.pin()
        await asyncio.sleep(1)

        beginner_channel = discord.utils.get(ctx.guild.channels, name='beginner-questions')
        message = await beginner_channel.send(beginner_message)
        await asyncio.sleep(1)
        await message.pin()
        await asyncio.sleep(1)

        book_channel = discord.utils.get(ctx.guild.channels, name='books')
        book_leaderboard_message = await book_channel.send("Book Leaderboard Placeholder")

        with open(f"cogs/guild_data.json") as json_file:
            data_dict = json.load(json_file)

        data_dict["book_leaderboard_message"] = book_leaderboard_message.id

        with open(f'cogs/guild_data.json', 'w') as json_file:
            json.dump(data_dict, json_file)

        await self.create_react_message(ctx)

        welcome_channel = discord.utils.get(ctx.guild.channels, name='welcome')
        await welcome_channel.send(invite_link_message)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def create_react_message(self, ctx):

        welcome_channel = discord.utils.get(ctx.guild.channels, name='welcome')
        reactions_message = await welcome_channel.send(reactions_string)

        for emoji_string in reaction_emojis:
            await asyncio.sleep(1)
            await reactions_message.add_reaction(emoji_string)

        with open(f"cogs/guild_data.json") as json_file:
            data_dict = json.load(json_file)

        data_dict["reactions_message_id"] = reactions_message.id

        with open(f'cogs/guild_data.json', 'w') as json_file:
            json.dump(data_dict, json_file)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def create_vn_messages(self, ctx):

        with open(f"cogs/guild_data.json") as json_file:
            data_dict = json.load(json_file)

        vn_channel = discord.utils.get(ctx.guild.channels, name='vn')

        pinned_messages = await vn_channel.pins()
        for message in pinned_messages:
            if message.author.id == self.bot.user.id:
                await asyncio.sleep(1)
                await message.unpin()

        monthly_vn_message = await vn_channel.send("Monthly VN message placeholder.")
        await asyncio.sleep(1)
        quarterly_vn_message = await vn_channel.send("Quarterly VN message placeholder.")
        await asyncio.sleep(1)
        leaderboard_1 = await vn_channel.send("Leaderboard 1 Placeholder")
        await asyncio.sleep(1)
        leaderboard_2 = await vn_channel.send("Leaderboard 2 Placeholder")
        await asyncio.sleep(1)
        leaderboard_3 = await vn_channel.send("Leaderboard 3 Placeholder")
        await asyncio.sleep(1)
        leaderboard_4 = await vn_channel.send("Leaderboard 4 Placeholder")
        await asyncio.sleep(1)

        await quarterly_vn_message.pin()
        await asyncio.sleep(1)
        await monthly_vn_message.pin()
        await asyncio.sleep(1)
        await leaderboard_4.pin()
        await asyncio.sleep(1)
        await leaderboard_3.pin()
        await asyncio.sleep(1)
        await leaderboard_2.pin()
        await asyncio.sleep(1)
        await leaderboard_1.pin()
        await asyncio.sleep(1)

        data_dict["monthly_vn_message"] = monthly_vn_message.id
        data_dict["quarterly_vn_message"] = quarterly_vn_message.id
        data_dict["leaderboard_1"] = leaderboard_1.id
        data_dict["leaderboard_2"] = leaderboard_2.id
        data_dict["leaderboard_3"] = leaderboard_3.id
        data_dict["leaderboard_4"] = leaderboard_4.id

        with open(f'cogs/guild_data.json', 'w') as json_file:
            json.dump(data_dict, json_file)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def create_bump_messages(self, ctx):

        # https://pastebin.com/sKYwGbav Disboard message.

        with open(f"cogs/guild_data.json") as json_file:
            data_dict = json.load(json_file)

        bump_channel = discord.utils.get(ctx.guild.channels, name='bump')

        leaderboard_1 = await bump_channel.send("leaderboard 1")
        await asyncio.sleep(1)
        leaderboard_2 = await bump_channel.send("leaderboard 2")
        await asyncio.sleep(1)

        data_dict["bump_leaderboard_1"] = leaderboard_1.id
        data_dict["bump_leaderboard_2"] = leaderboard_2.id

        await leaderboard_2.pin()
        await asyncio.sleep(1)
        await leaderboard_1.pin()
        await asyncio.sleep(1)

        with open(f'cogs/guild_data.json', 'w') as json_file:
            json.dump(data_dict, json_file)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def give_everyone_unranked_role(self, ctx):
        unranked_role = discord.utils.get(ctx.guild.roles, name='農奴 / Unranked')
        all_members = [member for member in ctx.guild.members if member.bot is False]

        for member in all_members:
            await asyncio.sleep(1)
            await member.add_roles(unranked_role)
            print(f"Gave unranked role to {str(member)}")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def restore_roles(self, ctx):
        guild_roles = [role.name for role in ctx.guild.roles]
        rank_roles = ['大王', '大公', '公爵', '侯爵', '伯爵 / N3', '子爵 / N4']
        illegal_roles = ["Admin", "Mod", "Muted", "Server Booster"]

        self.s3_client.download_file('djtbot', "rolesdata.json", 'data/rolesdata.json')

        with open(f"data/rolesdata.json") as json_file:
            rolesdict = json.load(json_file)

        for str_member_id in rolesdict:
            if "農奴 / Unranked" in rolesdict[str_member_id]:
                print("Member is unranked. Skipping.")
                continue

            roles_to_restore = [discord.utils.get(ctx.guild.roles, name=role) for role in rolesdict[str_member_id] if
                                role not in illegal_roles and role in guild_roles]
            if set(rolesdict[str_member_id]) & set(rank_roles):
                member = ctx.guild.get_member(int(str_member_id))
                if member:
                    await asyncio.sleep(1)
                    await member.add_roles(*roles_to_restore)
                    await asyncio.sleep(1)
                    await member.remove_roles(discord.utils.get(ctx.guild.roles, name="農奴 / Unranked"))

                    print(f"Restored the roles {', '.join([role.name for role in roles_to_restore])} to {member.name}.")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def create_djt(self, ctx):
        """Recreate the DJT Server. A channel called "revive" has to exist for the function to work. """
        if "revive" in [channel.name for channel in ctx.guild.channels]:

            await ctx.send("Condition fulfilled. Are you sure you want to recreate the DJT server? \n"
                           "Everything will be deleted. (y/n)")

            def check(message):
                return message.author == ctx.author

            confirmation_message = await self.bot.wait_for('message', timeout=10.0, check=check)
            if confirmation_message.content == "y":
                await ctx.send("Commencing recreation...")

                bots_found = await self.check_for_bots(ctx)
                if not bots_found:
                    return

                await ctx.send("Finished confirming bots.")

                await self.create_channels(ctx)
                await ctx.send("Finished creating channels.")

                await self.create_roles(ctx)
                await ctx.send("Finished creating roles.")

                await self.update_role_and_channel_permissions(ctx)
                await ctx.send("Finished editing permissions.")

                await self.create_messages(ctx)
                await ctx.send("Finished creating messages.")

                await self.create_vn_messages(ctx)
                await ctx.send("Finished creating VN messages.")

                await self.create_bump_messages(ctx)
                await ctx.send("Finished creating bump messages.")

                await self.write_ids(ctx)
                await ctx.send("Wrote ids to json file.")

                await self.give_everyone_unranked_role(ctx)
                await ctx.send("Gave everyone unranked role.")

                await self.restore_roles(ctx)
                await ctx.send("Restored user roles.")

                # await self.readd_emoji_list(ctx)
                # await ctx.send("Finished adding emoji.")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def write_ids(self, ctx):
        """Write server ids to json file."""

        with open(f"cogs/guild_data.json") as json_file:
            data_dict = json.load(json_file)

            data_dict["current_backup_server_id"] = backup_server_id
            data_dict["guild_id"] = ctx.guild.id

            data_dict["kotoba_id"] = bot_ids["Kotoba"]
            data_dict["nullposter_id"] = user_ids["nullposter"]
            data_dict["kaigen_user_id"] = user_ids["QM"]

            # Channel ids
            data_dict["guild_id"] = ctx.guild.id
            data_dict["welcome_channel_id"] = discord.utils.get(ctx.guild.channels, name='welcome').id
            data_dict["otaku_channel_id"] = discord.utils.get(ctx.guild.channels, name='otaku').id
            data_dict["vn_channel_id"] = discord.utils.get(ctx.guild.channels, name='vn').id
            data_dict["search_request_id"] = discord.utils.get(ctx.guild.channels, name='search-request').id
            data_dict["join_quiz_1_id"] = discord.utils.get(ctx.guild.channels, name='join-quiz').id
            data_dict["join_quiz_2_id"] = discord.utils.get(ctx.guild.channels, name='join-quiz2').id
            data_dict["bump_channel_id"] = discord.utils.get(ctx.guild.channels, name='bump').id
            data_dict["elite_mod_channel_id"] = discord.utils.get(ctx.guild.channels, name='elite-mod').id
            data_dict["manga_channel_id"] = discord.utils.get(ctx.guild.channels, name='manga').id

            # Role ids
            unranked_role_id = discord.utils.get(ctx.guild.roles, name='農奴 / Unranked').id
            n4_role_id = discord.utils.get(ctx.guild.roles, name='子爵 / N4').id
            n3_role_id = discord.utils.get(ctx.guild.roles, name='伯爵 / N3').id
            n2_role_id = discord.utils.get(ctx.guild.roles, name='侯爵').id
            n1_role_id = discord.utils.get(ctx.guild.roles, name='公爵').id
            taikou_role_id = discord.utils.get(ctx.guild.roles, name='大公').id
            daiou_role_id = discord.utils.get(ctx.guild.roles, name='大王').id
            muted_role_id = discord.utils.get(ctx.guild.roles, name='Muted').id
            student_role_id = discord.utils.get(ctx.guild.roles, name='Student').id
            quizzer_role_id = discord.utils.get(ctx.guild.roles, name='Quizzer').id
            quiz_god_role_id = discord.utils.get(ctx.guild.roles, name='Quiz God').id
            first_checkmark_id = discord.utils.get(ctx.guild.roles, name='✓').id
            second_checkmark_id = discord.utils.get(ctx.guild.roles, name='✓✓').id
            vn_manager_id = discord.utils.get(ctx.guild.roles, name='VN Manager').id
            bumper_role_id = discord.utils.get(ctx.guild.roles, name='Bumper').id
            position_reference_role_id = discord.utils.get(ctx.guild.roles, name='Pos. Reference Role').id
            mod_role_id = discord.utils.get(ctx.guild.roles, name='Mod').id
            admin_role_id = discord.utils.get(ctx.guild.roles, name='Admin').id

            try:
                booster_role_id = discord.utils.get(ctx.guild.roles, name='Server Booster').id
            except AttributeError:
                booster_role_id = None

            data_dict["mod_role_id"] = mod_role_id
            data_dict["admin_role_id"] = admin_role_id
            data_dict["first_checkmark_id"] = first_checkmark_id
            data_dict["second_checkmark_id"] = second_checkmark_id
            data_dict["vn_manager_id"] = vn_manager_id
            data_dict["student_role_id"] = student_role_id
            data_dict["quizzer_role_id"] = quizzer_role_id
            data_dict["quiz_god_role_id"] = quiz_god_role_id
            data_dict["unranked_role_id"] = unranked_role_id
            data_dict["n4_role_id"] = n4_role_id
            data_dict["booster_role_id"] = booster_role_id
            data_dict["muted_role_id"] = muted_role_id
            data_dict["bumper_role_id"] = bumper_role_id
            data_dict["position_reference_role_id"] = position_reference_role_id
            data_dict["quizranks"] = [unranked_role_id, n4_role_id, n3_role_id, n2_role_id, n1_role_id, taikou_role_id,
                                      daiou_role_id]
            data_dict["custom_role_permission"] = [daiou_role_id, taikou_role_id, booster_role_id, quiz_god_role_id,
                                                   quizzer_role_id]
            data_dict["custom_emoji_permission"] = [daiou_role_id, booster_role_id, quiz_god_role_id, quizzer_role_id]

            # User/bot ids
            data_dict["kotoba_id"] = bot_ids["Kotoba"]

            # Quiz information
            mycommands = {unranked_role_id: "(Join Quiz) Level 1:\n`k!quiz n4 nodelay atl=10 14 size=80 mmq=2`",
                          n4_role_id: "Level 2:\n`k!quiz n3 nodelay atl=10 18 size=60 mmq=1`",
                          n3_role_id: "Level 3:\n`k!quiz n2 nodelay atl=10 20 font=10 size=40 mmq=1`",
                          n2_role_id: "Level 4:\n`k!quiz n1 nodelay atl=9 25 font=7 size=35 mmq=1`",
                          n1_role_id: "Level 5:\n`k!quiz yoji_2k+yoji_j1k+2k+j1k+insane nodelay atl=12 30 font=10 size=30 mmq=1`",
                          taikou_role_id: "Level 6:\n`k!quiz yoji_1k+1k nodelay atl=12 35 font=10 size=30 mmq=1`",
                          daiou_role_id: "You have reached the highest level!"}

            data_dict["mycommands"] = mycommands

            # scorelimit, answertimelimitinms, fontsize, font, rankid, failedquestioncount
            myrankstructure = {
                "JLPT N4 Reading Quiz": (14, 10001, 80, 'any', n4_role_id, 1),

                "JLPT N3 Reading Quiz": (18, 10001, 60, 'any', n3_role_id, 0),

                "JLPT N2 Reading Quiz": (20, 10001, 40, 'AC Gyousho', n2_role_id, 0),

                "JLPT N1 Reading Quiz": (25, 9001, 35, 'Aoyagi Kouzan Gyousho', n1_role_id, 0),

                " Yojijukugo Kanken 2 (data from bu-sensei) Yojijukugo Kanken 1.5 (data from bu-sensei) Kanken 2級 Reading Quiz Kanken 準１級 Reading Quiz Insane Reading Quiz": (
                    30, 12001, 30, 'AC Gyousho', taikou_role_id, 0),

                " Yojijukugo Kanken 1 (data from bu-sensei) Kanken 1級 Reading Quiz": (
                    35, 12001, 30, 'AC Gyousho', daiou_role_id, 0)
            }

            data_dict["rank_structure"] = myrankstructure

        with open(f'cogs/guild_data.json', 'w') as json_file:
            json.dump(data_dict, json_file)

        await ctx.send("Wrote all ids.")

    @tasks.loop(minutes=60.0)
    async def sync_roles_new(self):
        """This task regularly syncs roles from the rolesdata.json file to the guild defined by backup_server_id."""

        if self.loop_iteration == 0:
            self.loop_iteration += 1

        else:
            print("Syncing roles from main server to backup server...")
            backup_guild = self.bot.get_guild(backup_server_id)
            announce_channel = backup_guild.get_channel(902919584577888286)

            self.s3_client.download_file('djtbot', "rolesdata.json", 'data/rolesdata.json')

            with open(f"data/rolesdata.json") as json_file:
                rolesdict = json.load(json_file)

            backup_members = [member.id for member in backup_guild.members if member.bot is False]
            saved_user_ids = [int(id_string) for id_string in rolesdict]
            saved_member_ids = [member_id for member_id in backup_members if member_id in saved_user_ids]

            for member_id in saved_member_ids:
                member = backup_guild.get_member(member_id)
                roles_already_given = [role for role in member.roles if
                                       role.name != 'Server Booster' and role.name != '農奴 / Unranked' and role.name != "@everyone"]
                roles_saved = [discord.utils.get(backup_guild.roles, name=role_string) for role_string in
                               rolesdict[str(member_id)]]
                roles_saved = [role for role in roles_saved if role is not None]
                illegal_roles = ["Admin", "Mod", "Muted", "Server Booster", "Emoji"]
                roles_to_give = [role for role in roles_saved if
                                 role not in roles_already_given and role.name not in illegal_roles]
                roles_to_remove = [role for role in roles_already_given if role not in roles_saved]

                if roles_to_give:
                    await asyncio.sleep(1)
                    await member.add_roles(*roles_to_give)
                    await asyncio.sleep(1)
                    await announce_channel.send(
                        f"Gave {', '.join([role.name for role in roles_to_give])} to {str(member)}")
                if roles_to_remove:
                    await asyncio.sleep(1)
                    await member.remove_roles(*roles_to_remove)
                    await asyncio.sleep(1)
                    await announce_channel.send(
                        f"Removed {', '.join([role.name for role in roles_to_remove])} from {str(member)}")

            # Make sure everyone has one rank role.
            unranked_role = discord.utils.get(backup_guild.roles, name='農奴 / Unranked')
            n4_role = discord.utils.get(backup_guild.roles, name='子爵 / N4')
            n3_role = discord.utils.get(backup_guild.roles, name='伯爵 / N3')
            n2_role = discord.utils.get(backup_guild.roles, name='侯爵')
            n1_role = discord.utils.get(backup_guild.roles, name='公爵')
            taikou_role = discord.utils.get(backup_guild.roles, name='大公')
            daiou_role = discord.utils.get(backup_guild.roles, name='大王')
            rank_roles = [unranked_role, n4_role, n3_role, n2_role, n1_role, taikou_role, daiou_role]

            all_members = [member for member in backup_guild.members if member.bot is False]
            for member in all_members:
                user_rank_roles = [role for role in member.roles if role in rank_roles]
                if len(user_rank_roles) == 0:
                    await asyncio.sleep(1)
                    await member.add_roles(unranked_role)
                    await asyncio.sleep(1)
                    await announce_channel.send(f"Gave {unranked_role.name} role to {str(member)}")

                if len(user_rank_roles) == 2:
                    await asyncio.sleep(1)
                    await member.remove_roles(unranked_role)
                    await asyncio.sleep(1)
                    await announce_channel.send(f"Removed {unranked_role.name} role from {str(member)}")

            await announce_channel.send("Finished syncing roles with main server.")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def download_emoji(self, ctx):
        """Command to download all emoji to data/emojis/"""

        original_guild = self.bot.get_guild(862723250676170852)
        emoji_assets = [(emoji.name, emoji.url) for emoji in original_guild.emojis]
        for emoji_asset in emoji_assets:
            await asyncio.sleep(1)
            await emoji_asset[1].save(f"data/emojis/full_backup/{emoji_asset[0]}")
        await ctx.send("Downloaded emoji.")


def setup(bot):
    bot.add_cog(Restoration(bot))
