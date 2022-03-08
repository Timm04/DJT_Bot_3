"""Cog responsible for giving out roles in response to reactions."""

import discord
from discord.ext import commands
import json

#############################################################
# Variables (Temporary)
with open(f"cogs/guild_data.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]
    role_assignment_message_id = data_dict["reactions_message_id"]

    # Roles that can't get ranks
    unranked_role_id = data_dict["unranked_role_id"]
    muted_role_id = data_dict["muted_role_id"]
    booster_role_id = data_dict["booster_role_id"]

    # Patreon role ids
    student_id = data_dict["student_role_id"]
    quizzer_id = data_dict["quizzer_role_id"]
    quiz_god_id = data_dict["quiz_god_role_id"]

    # Can't get VN challenge role
    n4_role_id = data_dict["n4_role_id"]
#############################################################

class Reactions(commands.Cog):
    """Reaction for event roles."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guild_id)
        self.vnreadingrole = discord.utils.get(self.myguild.roles, name='VN Challenge')
        self.bookclubrole = discord.utils.get(self.myguild.roles, name='Book Club')
        self.manga_role = discord.utils.get(self.myguild.roles, name="Manga Club")
        self.streamrole = discord.utils.get(self.myguild.roles, name='Reading Stream')
        self.conversationrole = discord.utils.get(self.myguild.roles, name='Conversation')
        self.movierole = discord.utils.get(self.myguild.roles, name='Movie')
        self.bumprole = discord.utils.get(self.myguild.roles, name='Bumper')
        self.eventrole = discord.utils.get(self.myguild.roles, name='Event')

    async def vn_role_allowed(self, role_ids):
        allowed_role_ids = [booster_role_id, student_id, quizzer_id, quiz_god_id]
        for role_id in allowed_role_ids:
            if role_id in role_ids:
                return True
        if unranked_role_id in role_ids:
            return False
        elif n4_role_id in role_ids:
            return True
        else:
            return True

    async def event_roles_allowed(self, role_ids, private_channel):

        if muted_role_id in role_ids:
            await private_channel.send("You can't get event roles while muted.")
            return False

        allowed_role_ids = [booster_role_id, student_id, quizzer_id, quiz_god_id]
        for role_id in allowed_role_ids:
            if role_id in role_ids:
                return True

        if booster_role_id in role_ids:
            return True
        elif unranked_role_id in role_ids:
            await private_channel.send(f"You have to pass the N4 quiz before you have access to event roles!")
            return False
        else:
            return True

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, rawevent: discord.RawReactionActionEvent):

        if rawevent.message_id == role_assignment_message_id:
            try:
                reaction_member = self.myguild.get_member(rawevent.user_id)
            except AttributeError:
                return

            try:
                await reaction_member.create_dm()
                private_channel = reaction_member.dm_channel
            except discord.errors.HTTPException:
                pass

            user_role_ids = [role.id for role in reaction_member.roles]
            roles_allowed = await self.event_roles_allowed(user_role_ids, private_channel)
            if not roles_allowed:
                return

            if str(rawevent.emoji) == "🖋️":
                if await self.vn_role_allowed(user_role_ids):
                    await reaction_member.add_roles(self.vnreadingrole)
                    await private_channel.send(f"{reaction_member.mention} You joined the VN challenge!")
                else:
                    await private_channel.send(f"{reaction_member.mention} You have to pass the N3 quiz before you have "
                                               f"access to the VN Challenge.\n Type `$levelup`."
                                               f"\n Alternatively you can **boost** the server.")
            elif str(rawevent.emoji) == "📖":
                await reaction_member.add_roles(self.bookclubrole)
                await private_channel.send(f"{reaction_member.mention} You joined the book club!")
            elif str(rawevent.emoji) == "📹":
                await reaction_member.add_roles(self.streamrole)
                await private_channel.send(f"{reaction_member.mention} You joined the reading stream!")
            elif str(rawevent.emoji) == "💬":
                await reaction_member.add_roles(self.conversationrole)
                await private_channel.send(f"{reaction_member.mention} You joined the conversation club!")
            elif str(rawevent.emoji) == "🎥":
                await reaction_member.add_roles(self.movierole)
                await private_channel.send(f"{reaction_member.mention} You joined the movie club!")
            elif str(rawevent.emoji) == "❗":
                await reaction_member.add_roles(self.bumprole)
                await private_channel.send(f"{reaction_member.mention} You got the bump role!")
            elif str(rawevent.emoji) == "⭐":
                await reaction_member.add_roles(self.eventrole)
                await private_channel.send(f"{reaction_member.mention} You got the event role!")
            elif str(rawevent.emoji) == "🥭":
                await reaction_member.add_roles(self.manga_role)
                await private_channel.send(f"{reaction_member.mention} You got the manga club role!")
            else:
                react_channel = discord.utils.get(self.myguild.channels, name='welcome')
                reaction_message = await react_channel.fetch_message(role_assignment_message_id)
                await reaction_message.remove_reaction(rawevent.emoji, rawevent.member)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, rawevent: discord.RawReactionActionEvent):
        if rawevent.message_id == role_assignment_message_id:

            reaction_member = self.myguild.get_member(rawevent.user_id)

            await reaction_member.create_dm()
            private_channel = reaction_member.dm_channel

            if str(rawevent.emoji) == "🖋️":
                await reaction_member.remove_roles(self.vnreadingrole)
                await private_channel.send(f"{reaction_member.mention} You left the VN challenge.")
            elif str(rawevent.emoji) == "📖":
                await reaction_member.remove_roles(self.bookclubrole)
                await private_channel.send(f"{reaction_member.mention} You left the book club.")
            elif str(rawevent.emoji) == "📹":
                await reaction_member.remove_roles(self.streamrole)
                await private_channel.send(f"{reaction_member.mention} You left the reading stream.")
            elif str(rawevent.emoji) == "💬":
                await reaction_member.remove_roles(self.conversationrole)
                await private_channel.send(f"{reaction_member.mention} You left the conversation club!")
            elif str(rawevent.emoji) == "🎥":
                await reaction_member.remove_roles(self.movierole)
                await private_channel.send(f"{reaction_member.mention} You left the movie club!")
            elif str(rawevent.emoji) == "❗":
                await reaction_member.remove_roles(self.bumprole)
                await private_channel.send(f"{reaction_member.mention} You lost the bump role.")
            elif str(rawevent.emoji) == "⭐":
                await reaction_member.remove_roles(self.eventrole)
                await private_channel.send(f"{reaction_member.mention} You lost the event role.")
            elif str(rawevent.emoji) == "🥭":
                await reaction_member.remove_roles(self.manga_role)
                await private_channel.send(f"{reaction_member.mention} You lost the manga club role!")

def setup(bot):
    bot.add_cog(Reactions(bot))