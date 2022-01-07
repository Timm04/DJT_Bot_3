import discord
from discord.ext import commands
import json

with open("cogs/guild_data.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]

class NotablePosts(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.added_message_ids = dict()

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guild_id)
        self.log_channel = discord.utils.get(self.myguild.channels, name="notable-posts")

    async def count_reactions(self, reaction_message):
        post_qualifies = False
        for reaction in reaction_message.reactions:
            if reaction.count >= 10:
                post_qualifies = True

        if post_qualifies:
            total_count = 0
            for reaction in reaction_message.reactions:
                total_count += reaction.count
            if total_count >= 16:
                return total_count
            else:
                return False
        else:
            return False

    async def create_embed(self, reaction_message):
        myembed = discord.Embed(description=f"[Jump To Message]({reaction_message.jump_url})")
        myembed.set_author(name=str(reaction_message.author), icon_url=str(reaction_message.author.avatar_url))

        if reaction_message.content:
            myembed.add_field(name="Content:", value=reaction_message.content, inline=False)

        reaction_string = [f"{reaction.count} {reaction.emoji}" for reaction in reaction_message.reactions]
        reaction_string = ", ".join(reaction_string)

        myembed.add_field(name="Reactions:", value=reaction_string, inline=False)
        if reaction_message.attachments:
            myembed.add_field(name="Media:", value="The post contained the following image:", inline=False)
            myembed.set_image(url=reaction_message.attachments[0].url)

        return myembed

    async def create_message(self, reaction_message, reaction_count):
        myembed = await self.create_embed(reaction_message)
        log_message = await self.log_channel.send(embed=myembed)
        self.added_message_ids[reaction_message.id] = (log_message.id, reaction_count)

    async def edit_message(self, reaction_message, log_message_count, new_reaction_count):
        log_message_id = log_message_count[0]
        log_message = await self.log_channel.fetch_message(log_message_id)
        old_reaction_count = log_message_count[1]
        myembed = await self.create_embed(reaction_message)
        if new_reaction_count - old_reaction_count >= 5:
            await log_message.edit(embed=myembed)
            self.added_message_ids[reaction_message.id] = (log_message, new_reaction_count)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user):
        if reaction.message.guild.id == guild_id and reaction.message.channel.id != self.log_channel.id:
            enough_reactions = await self.count_reactions(reaction.message)
            if enough_reactions:
                if reaction.message.id not in self.added_message_ids:
                    await self.create_message(reaction.message, enough_reactions)
                else:
                    await self.edit_message(reaction.message, self.added_message_ids[reaction.message.id], enough_reactions)

def setup(bot):
    bot.add_cog(NotablePosts(bot))
