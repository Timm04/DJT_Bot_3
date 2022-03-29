"""Cog for the Manga challenge"""
import botocore.exceptions
import discord
from discord.ext import commands
from discord.ext import tasks
import json
import boto3
import asyncio


def is_manga_manager():
    async def predicate(ctx):
        run_command = False
        if ctx.author.id == 922627087020482651:
            run_command = True
        return run_command

    return commands.check(predicate)

#############################################################
# Variables (Temporary)
with open(f"cogs/guild_data.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]

class manga(commands.Cog):
    """Manga cog"""

    def __init__(self, bot):
        self.bot = bot
        self.s3_client = boto3.client('s3')

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guild_id)
        self.manga_channel = discord.utils.get(self.myguild.channels, name="manga")
        await asyncio.sleep(600)
        await self.create_rules_post()
        self.update_posts.start()
        self.give_roles.start()

    def pull_all_records(self, fname):
        try:
            self.s3_client.download_file('djtbot', fname, f'data/{fname}')
        except botocore.exceptions.ClientError:
            try:
                with open(f"data/{fname}") as json_file:
                    data_dict = json.load(json_file)
                    return data_dict
            except FileNotFoundError:
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
    @is_manga_manager()
    async def add_manga(self, ctx, manga_code, *, manga_name):
        manga_database = self.pull_all_records("manga_database.json")
        manga_database[manga_code] = manga_name
        self.push_all_records(manga_database, "manga_database.json")
        await self.update_posts()
        await ctx.send(f"Added {manga_name} as {manga_code} to database.")

    @commands.command(hidden=True)
    @is_manga_manager()
    async def remove_manga(self, ctx, manga_code):
        manga_database = self.pull_all_records("manga_database.json")
        manga_name = manga_database[manga_code]
        manga_database.remove(manga_code)
        self.push_all_records(manga_database, "manga_database.json")
        await self.update_posts()
        await ctx.send(f"Remove {manga_name} from database.")

    @commands.command()
    @commands.guild_only()
    async def review_manga(self, ctx, manga_code, *, review):
        banned_list = self.pull_all_records("manga_banned_users.json")
        if str(ctx.author.id) in banned_list:
            await ctx.send("You are banned from the manga challenge.")
            return

        if ctx.channel != self.manga_channel:
            await ctx.send("Please use this command in the manga channel.")
            return

        if len(review) < 600:
            await ctx.send("Your review is too short. A review has to be at least 600 symbols long.")
            return

        if len(review) > 1900:
            await ctx.send("Your review is too long. Keep it below 1900 symbols.")
            return

        manga_database = self.pull_all_records("manga_database.json")
        if manga_code not in manga_database:
            await ctx.send("This manga is not in the database.")
            return

        manga_name = manga_database[manga_code]

        manga_leaderboard = self.pull_all_records("manga_leaderboard.json")
        user_id = str(ctx.author.id)
        read_manga = manga_leaderboard.get(user_id)
        if not read_manga:
            read_manga = [manga_code]
            manga_leaderboard[user_id] = read_manga
        else:
            if manga_code in read_manga:
                await ctx.send("You already reviewed this manga!")
                return
            else:
                read_manga.append(manga_code)
                manga_leaderboard[user_id] = read_manga
        await self.manga_channel.send(
            f"{ctx.author} (ID:{ctx.author.id}) just created the following review for the manga {manga_name}:"
            f"\n`{review}`")
        await self.manga_channel.send(f"Awarded a point to {ctx.author.mention}: {len(read_manga) - 1} -> {len(read_manga)}")
        self.push_all_records(manga_leaderboard, "manga_leaderboard.json")

    @tasks.loop(minutes=60.0)
    async def update_posts(self):
        manga_leaderboard = self.pull_all_records("manga_leaderboard.json")
        manga_database = self.pull_all_records("manga_database.json")

        leaderboard_pins = []
        database_pins = []

        manga_pins = await self.manga_channel.pins()
        for pin in manga_pins:
            if pin.content.startswith("Manga leaderboard:"):
                leaderboard_pins.append(pin)
            elif pin.content.startswith("All voted mangas:"):
                database_pins.append(pin)

        database_msg = "All voted mangas:\n"
        message_count = 0
        for manga_code, manga_description in manga_database.items():
            database_msg += f"\n - {manga_description}. Code: `{manga_code}`"
            if len(database_msg) > 1800:
                try:
                    await database_pins[message_count].edit(content=database_msg)
                    message_count += 1
                except IndexError:
                    new_database_message = await self.manga_channel.send(database_msg)
                    await new_database_message.pin()
                    database_msg = "All voted mangas:\n"

        if database_msg:
            try:
                await database_pins[message_count].edit(content=database_msg)
            except IndexError:
                new_database_message = await self.manga_channel.send(database_msg)
                await new_database_message.pin()

        leaderboard_msg = "Manga leaderboard:\n"
        message_count = 0
        for rank, (user_id, watched_manga_list) in enumerate(sorted(manga_leaderboard.items(), key=lambda x: len(x[1]), reverse=True)):
            leaderboard_msg += f'{rank + 1}. <@!{user_id}> : {len(watched_manga_list)} 漫画 read.\n'
            if len(leaderboard_msg) > 1800:
                try:
                    await leaderboard_pins[message_count].edit(content=leaderboard_msg)
                    message_count += 1
                except IndexError:
                    new_leaderboard_message = await self.manga_channel.send(leaderboard_msg)
                    await new_leaderboard_message.pin()
                    leaderboard_msg = "Manga leaderboard:\n"

        if leaderboard_msg:
            try:
                await leaderboard_pins[message_count].edit(content=leaderboard_msg)
            except IndexError:
                new_leaderboard_message = await self.manga_channel.send(leaderboard_msg)
                await new_leaderboard_message.pin()

    @tasks.loop(minutes=10)
    async def give_roles(self):
        leaderboard = self.pull_all_records("manga_leaderboard.json")
        for user_data in leaderboard.items():
            user = self.myguild.get_member(int(user_data[0]))
            if user:
                role_names = [role.name for role in user.roles]
                if str(len(user_data[1])) + "🥭" in role_names:
                    continue

                manga_reward_role = discord.utils.get(self.myguild.roles, name=str(len(user_data[1]))+"🥭")
                if not manga_reward_role:
                    reference_pos_role = discord.utils.get(self.myguild.roles, name=f"✓✓")
                    reference_pos = reference_pos_role.position - 1

                    manga_reward_role = await self.myguild.create_role(name=str(len(user_data[1]))+"🥭",
                                                                      colour=discord.Colour(12423186))
                    positions = {manga_reward_role: reference_pos}
                    await self.myguild.edit_role_positions(positions)

                await user.add_roles(manga_reward_role)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def update_manga(self, ctx):
        await self.update_posts()
        await self.give_roles()
        await self.create_rules_post()
        await ctx.send("Done.")

    @commands.command(hidden=True)
    @is_manga_manager()
    async def clear_user_from_manga(self, ctx, id):
        manga_leaderboard = self.pull_all_records("manga_leaderboard.json")
        del manga_leaderboard[str(id)]
        self.push_all_records(manga_leaderboard, "manga_leaderboard.json")
        await ctx.send(f"Removed user with the id {id} from the database")

    @commands.command(hidden=True)
    @is_manga_manager()
    async def ban_user_from_manga(self, ctx, id):
        manga_leaderboard = self.pull_all_records("manga_leaderboard.json")
        del manga_leaderboard[str(id)]
        self.push_all_records(manga_leaderboard, "manga_leaderboard.json")

        banned_list = self.pull_all_records("manga_banned_users.json")
        banned_list.append(id)
        with open(f'data/manga_banned_users.json', 'w') as json_file:
            json.dump(banned_list, json_file)
        self.s3_client.upload_file(f'data/manga_banned_users.json', "djtbot", f'manga_banned_users.json')

        await ctx.send("User has been banned.")

    async def create_rules_post(self):
        rule_message_string = """Manga channel rules:
To get points on the leaderboard write `$review_manga manga_code your_review`. 
A review has to be at least 600 characters long.
Should you abuse this feature or write a fake review you will be banned from the manga challenge and all your points will be revoked."""

        manga_pins = await self.manga_channel.pins()
        for pin in manga_pins:
            if pin.content.startswith("Manga channel rules:"):
                return

        rule_message = await self.manga_channel.send(rule_message_string)
        await rule_message.pin()


def setup(bot):
    bot.add_cog(manga(bot))
