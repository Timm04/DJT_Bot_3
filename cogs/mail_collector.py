import discord
from discord.ext import commands
import boto3
import json
import re

class MailCollector(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.s3_client = boto3.client('s3')
        self.fname = "mail_collection.json"
        self.mail_re = re.compile(r"""(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9]))\.){3}(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9])|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])""")

    def pull_all_records(self):
        self.s3_client.download_file('djtbot', self.fname, f'data/{self.fname}')
        with open(f"data/{self.fname}") as json_file:
            mail_dict = json.load(json_file)
        return mail_dict

    def push_all_records(self, mail_dict):
        with open(f'data/{self.fname}', 'w') as json_file:
            json.dump(mail_dict, json_file)
        self.s3_client.upload_file(f'data/{self.fname}', "djtbot", f'{self.fname}')

    @commands.command()
    async def addmail(self, ctx, mail):
        """Add your email to the DJT newsletter. Great deals like the DJT Japanese Pro Deck for $500/month."""
        user_id = str(ctx.author.id)
        mail_dict = self.pull_all_records()
        if self.mail_re.match(mail):
            mail_dict[user_id] = mail
            self.push_all_records(mail_dict)
            await ctx.send("Added your mail to the newsletter")
        else:
            await ctx.send("This is not a valid email.")
            return

def setup(bot):
    bot.add_cog(MailCollector(bot))
