"""Cog for the Anime challenge"""
import botocore.exceptions
import discord
from discord.ext import commands
from discord.ext import tasks
import json
import boto3
import asyncio


def is_anime_manager():
    async def predicate(ctx):
        run_command = False
        if ctx.author.id == 83438216237027328 or ctx.author.id == 922627087020482651:
            run_command = True
        return run_command

    return commands.check(predicate)

#############################################################
# Variables (Temporary)
with open(f"cogs/guild_data.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]


class Anime(commands.Cog):
    """VN leaderboard and challenge"""

    def __init__(self, bot):
        self.bot = bot
        self.s3_client = boto3.client('s3')

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guild_id)
        self.anime_channel = discord.utils.get(self.myguild.channels, name="anime")
        await asyncio.sleep(600)
        await self.create_rules_post()
        self.update_posts.start()
        self.give_roles.start()

    def pull_all_records(self, fname):
        try:
            self.s3_client.download_file('djtbot', fname, f'data/{fname}')
        except botocore.exceptions.ClientError:
            empty_dict = dict()
            return empty_dict

        with open(f"data/{fname}") as json_file:
            data_dict = json.load(json_file)

        return data_dict

    def push_all_records(self, data_dict, fname):
        with open(f'data/{fname}', 'w') as json_file:
            json.dump(data_dict, json_file)
        self.s3_client.upload_file(f'data/{fname}', "djtbot", f'{fname}')

    @commands.command(hidden=True)
    @is_anime_manager()
    async def add_anime(self, ctx, anime_code, *, anime_name):
        anime_database = self.pull_all_records("anime_database.json")
        anime_database[anime_code] = anime_name
        self.push_all_records(anime_database, "anime_database.json")
        await self.update_posts()
        await ctx.send(f"Added {anime_name} as {anime_code} to database.")

    @commands.command(hidden=True)
    @is_anime_manager()
    async def remove_anime(self, ctx, anime_code):
        anime_database = self.pull_all_records("anime_database.json")
        anime_name = anime_database[anime_code]
        anime_database.remove(anime_code)
        self.push_all_records(anime_database, "anime_database.json")
        await self.update_posts()
        await ctx.send(f"Remove {anime_name} from database.")

    @commands.command()
    @commands.guild_only()
    async def review(self, ctx, anime_code, *, review):
        banned_list = self.pull_all_records("anime_banned_users.json")
        if str(ctx.author.id) in banned_list:
            await ctx.send("You are banned from the anime challenge.")
            return

        if ctx.channel != self.anime_channel:
            await ctx.send("Please use this command in the anime channel.")
            return

        if len(review) < 600:
            await ctx.send("Your review is too short. A review has to be at least 600 symbols long.")
            return

        if len(review) > 1900:
            await ctx.send("Your review is too long. Keep it below 1900 symbols.")
            return

        anime_database = self.pull_all_records("anime_database.json")
        if anime_code not in anime_database:
            await ctx.send("This anime is not in the database.")
            return

        anime_name = anime_database[anime_code]

        anime_leaderboard = self.pull_all_records("anime_leaderboard.json")
        user_id = str(ctx.author.id)
        watched_anime = anime_leaderboard.get(user_id)
        if not watched_anime:
            watched_anime = [anime_code]
            anime_leaderboard[user_id] = watched_anime
        else:
            if anime_code in watched_anime:
                await ctx.send("You already reviewed this anime!")
                return
        await self.anime_channel.send(
            f"{ctx.author} (ID:{ctx.author.id}) just created the following review for the anime {anime_name}:"
            f"\n`{review}`")
        await self.anime_channel.send(f"Awarded a point to {ctx.author.mention}: {len(watched_anime) - 1} -> {len(watched_anime)}")
        self.push_all_records(anime_leaderboard, "anime_leaderboard.json")

    @tasks.loop(minutes=60.0)
    async def update_posts(self):
        anime_leaderboard = self.pull_all_records("anime_leaderboard.json")
        anime_database = self.pull_all_records("anime_database.json")

        leaderboard_pins = []
        database_pins = []

        anime_pins = await self.anime_channel.pins()
        for pin in anime_pins:
            if pin.content.startswith("Anime leaderboard:"):
                leaderboard_pins.append(pin)
            elif pin.content.startswith("All voted animes:"):
                database_pins.append(pin)

        database_msg = "All voted animes:\n"
        message_count = 0
        for anime_code, anime_description in anime_database.items():
            database_msg += f"\t - {anime_description}. Code: `{anime_code}`"
            if len(database_msg) > 1800:
                try:
                    await database_pins[message_count].edit(content=database_msg)
                    message_count += 1
                except IndexError:
                    new_database_message = await self.anime_channel.send(database_msg)
                    await new_database_message.pin()
                    database_msg = "All voted animes:\n"

        if database_msg:
            try:
                await database_pins[message_count].edit(content=database_msg)
            except IndexError:
                new_database_message = await self.anime_channel.send(database_msg)
                await new_database_message.pin()

        leaderboard_msg = "Anime leaderboard:\n"
        message_count = 0
        for rank, (user_id, watched_anime_list) in enumerate(sorted(anime_leaderboard.items(), key=lambda x: len(x[1]), reverse=True)):
            leaderboard_msg += f'{rank + 1}. <@!{user_id}> : {len(watched_anime_list)} アニメ watched.\n'
            if len(leaderboard_msg) > 1800:
                try:
                    await leaderboard_pins[message_count].edit(content=leaderboard_msg)
                    message_count += 1
                except IndexError:
                    new_leaderboard_message = await self.anime_channel.send(leaderboard_msg)
                    await new_leaderboard_message.pin()
                    leaderboard_msg = "Anime leaderboard:\n"

        if leaderboard_msg:
            try:
                await leaderboard_pins[message_count].edit(content=leaderboard_msg)
            except IndexError:
                new_leaderboard_message = await self.anime_channel.send(leaderboard_msg)
                await new_leaderboard_message.pin()

    @tasks.loop(minutes=10)
    async def give_roles(self):
        leaderboard = self.pull_all_records("anime_leaderboard.json")
        for user_data in leaderboard.items():
            user = self.myguild.get_member(int(user_data[0]))
            if user:
                for role in user.roles:
                    if role.name == str(len(user_data[1])) + "📺":
                        return

                anime_reward_role = discord.utils.get(self.myguild.roles, name=str(len(user_data[1]))+"📺")
                if not anime_reward_role:
                    reference_pos_role = discord.utils.get(self.myguild.roles, name=f"✓✓")
                    reference_pos = reference_pos_role.position - 1

                    anime_reward_role = await self.myguild.create_role(name=str(len(user_data[1]))+"📺",
                                                                      colour=discord.Colour(6713472))
                    positions = {anime_reward_role: reference_pos}
                    await self.myguild.edit_role_positions(positions)

                await user.add_roles(anime_reward_role)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def update_anime(self, ctx):
        await self.update_posts()
        await self.give_roles()
        await ctx.send("Done.")

    @commands.command()
    @is_anime_manager()
    async def clear_user(self, ctx, id):
        anime_leaderboard = self.pull_all_records("anime_leaderboard.json")
        del anime_leaderboard[str(id)]
        self.push_all_records(anime_leaderboard, "anime_leaderboard.json")
        await ctx.send(f"Removed user with the id {id} from the database")

    @commands.command()
    @is_anime_manager()
    async def ban_user(self, ctx, id):
        anime_leaderboard = self.pull_all_records("anime_leaderboard.json")
        del anime_leaderboard[str(id)]
        self.push_all_records(anime_leaderboard, "anime_leaderboard.json")

        banned_list = self.pull_all_records("anime_banned_users.json")
        banned_list.append(id)
        with open(f'data/anime_banned_users.json', 'w') as json_file:
            json.dump(banned_list, json_file)
        self.s3_client.upload_file(f'data/anime_banned_users.json', "djtbot", f'anime_banned_users.json')

        await ctx.send("User has been banned.")

    async def create_rules_post(self):
        rule_message_string = """Anime channel rules:
To get points on the leaderboard write `$review anime_code your_review`. 
A review has to be at least 600 characters long.
Should you abuse this feature or write a fake review you will be banned from the anime challenge and all your points will be revoked."""

        anime_pins = await self.anime_channel.pins()
        for pin in anime_pins:
            if pin.content.startswith("Anime channel rules:"):
                return

        rule_message = await self.anime_channel.send(rule_message_string)
        await rule_message.pin()


def setup(bot):
    bot.add_cog(Anime(bot))
