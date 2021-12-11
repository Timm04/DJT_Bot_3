"""This cog enables users to search for Japanese sentence examples in an Anime subtitle database. The corresponding
example is then fetched from a video database hosted on Amazon S3."""

import discord
from discord.ext import commands
import boto3
import srt
import os
import asyncio
import datetime
import subprocess
import pickle
import json

###
with open(f"cogs/guild_data.json") as json_file:
    data_dict = json.load(json_file)
    anime_request_allowed_channels = [data_dict["search_request_id"]]

###

class AnimeCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.s3_client = boto3.client('s3')
        self.subtitle_data = list()

    @commands.command(hidden=True)
    @commands.is_owner()
    async def create_sub_data(self, ctx):
        subtitle_files = [subtitle for subtitle in os.listdir('data/subs/') if subtitle.endswith('.srt')]
        for counter, subtitle_name in enumerate(subtitle_files):
            with open(fr'data/subs/{subtitle_name}', encoding='utf-8') as subtitle_file:
                subtitle_text = subtitle_file.read()
                try:
                    subtitle_generator = srt.parse(subtitle_text)
                    search_pairs = [(subtitle.index, subtitle.content) for subtitle in subtitle_generator]
                except srt.SRTParseError:
                    print(f"Subtitle excluded due to error: {subtitle_name}")
                    continue
                self.subtitle_data.append((f'{subtitle_name}', search_pairs))
                print(f"Loaded {counter + 1} out of {len(subtitle_files)} subtitles. ({round(counter/ len(subtitle_files), 4) * 100}%)")

        with open("data/subs/subs_data", "wb") as subsdata:
            pickle.dump(self.subtitle_data, subsdata)

        await ctx.send("Done.")

    async def get_sub_timings(self, subtitle_name, subtitle_index):
        with open(fr'data/subs/{subtitle_name}', encoding='utf-8') as subtitle_file:
            subtitle_text = subtitle_file.read()
            subtitle_generator = srt.parse(subtitle_text)
            all_subtitles = list(subtitle_generator)
            indexes_to_extract = list(range(subtitle_index-2, subtitle_index+3))
            subtitle_lines = [subtitle for subtitle in all_subtitles if subtitle.index in indexes_to_extract]
            content = " 　".join([subtitle.content for subtitle in subtitle_lines])
            if len(subtitle_lines) >= 5:
                beginning_time = subtitle_lines[1].start
            else:
                beginning_time = subtitle_lines[0].start - datetime.timedelta(seconds=5)
            end_time = subtitle_lines[-1].end + datetime.timedelta(seconds=4)
            return content, beginning_time, end_time

    async def edit_results_post(self, results, results_msg, beginning_index, end_index, japanese_input):
        myembed = discord.Embed(title=f"{len(results)} results for {japanese_input}")
        for result in results[beginning_index:end_index]:
            myembed.add_field(name=f"{result[0]} in {result[1]}", value=f"{result[2]}", inline=False)
        if len(results) >= 5:
            myembed.set_footer(text="... not all results displayed but you can pick any index.\n"
                                    "Pick an index to retrieve a scene next.")
        else:
            myembed.set_footer(text="Pick an index to retrieve a scene next.")

        await results_msg.edit(embed=myembed)

    async def get_nearest_key_frame_time(self, filename, beginning_time):
        path = "data/video/"
        cmd = f"ffprobe -v error -skip_frame nokey -show_entries frame=pkt_pts_time -select_streams v -of csv=p=0 {path + filename}"
        key_frames = subprocess.check_output(cmd, shell=True).decode().split()
        print("We have the following key frames: ", key_frames)
        key_frame_times = []
        for key_frame_seconds in key_frames:
            seconds, microseconds = key_frame_seconds.split(".")
            time = datetime.timedelta(seconds=float(seconds), microseconds=float(microseconds) - 1)
            key_frame_times.append(time)

        last_key_frame_time = [time for time in key_frame_times if beginning_time.total_seconds() - time.total_seconds() > 0][-1]
        if last_key_frame_time.total_seconds() <= 0:
            last_key_frame_time = last_key_frame_time.resolution
        return last_key_frame_time

    async def fix_times(self, beginning_time, end_time, filename):
        # Fix beginning time below zero
        if beginning_time.total_seconds() <= 0:
            beginning_time = beginning_time.resolution

        # Fix end time after end
        video_length_cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {filename}"
        video_lengths = subprocess.check_output(video_length_cmd, shell=True).decode().split('.')
        video_length = datetime.timedelta(seconds=float(video_lengths[0]), microseconds=float(video_lengths[1]))
        if video_length.total_seconds() - end_time.total_seconds() <= 1:
            end_time = video_length

        return beginning_time, end_time

    async def create_video(self, filename, beginning_time, end_time):
        path = "data/video/"
        await self.fix_times(beginning_time, end_time, path + filename)
        previous_key_frame_time = await self.get_nearest_key_frame_time(filename, beginning_time)
        start = "0" + str(previous_key_frame_time)[0:14]
        end_time = end_time - previous_key_frame_time
        end = "0" + str(end_time)[0:7]
        # cmd = f"ffmpeg -avoid_negative_ts 1 -i {path + filename} -ss {start} -to {end} -c copy {path}result_{filename[:-3] + 'mp4'}"
        cmd = f"ffmpeg -ss {start} -i {path + filename} -to {end} -c copy -avoid_negative_ts make_zero {path}result_{filename[:-3] + 'mp4'}"
        os.system(cmd)

    @commands.Cog.listener()
    async def on_ready(self):
        with open("data/subs/subs_data", "rb") as subsdata:
            self.subtitle_data = pickle.load(subsdata)

        print(f"Loaded subtitle data with {len(self.subtitle_data)} files.")

    async def download_file(self, filename):
        self.s3_client.download_file("djtvideoarchive", f"{filename}", f"data/video/{filename}")

    @commands.command()
    @commands.guild_only()
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    async def request(self, ctx, japanese_input: str):
        """`<japanese>` Search for an Anime scene with the requested Japanese input."""
        if ctx.channel.id not in anime_request_allowed_channels:
            await ctx.send("Please use this command in the 'search-request' channel. Thank you.")
            return

        await ctx.send(F"Searching for: {japanese_input}")
        results = []
        foundindex = 0
        for filename, subdata in self.subtitle_data:
            for srtindex, content in subdata:
                if japanese_input not in content:
                    continue

                foundindex += 1
                result = (foundindex, filename, content, srtindex)
                results.append(result)

        if len(results) == 0:
            await ctx.send("No results.")
            return

        myembed = discord.Embed(title=f"{len(results)} results for {japanese_input}")
        for result in results[0:5]:
            myembed.add_field(name=f"{result[0]} in {result[1]}", value=f"{result[2]}", inline=False)
        if len(results) >= 5:
            myembed.set_footer(text="... not all results displayed but you can pick any index.\n"
                                    "Pick an index to retrieve a scene next.")
        else:
            myembed.set_footer(text="Pick an index to retrieve a scene next.")

        results_message = await ctx.send(embed=myembed)
        await results_message.add_reaction('1️⃣')
        await results_message.add_reaction('2️⃣')
        await results_message.add_reaction('3️⃣')
        await results_message.add_reaction('4️⃣')
        await results_message.add_reaction('5️⃣')
        await results_message.add_reaction('⬅️')
        await results_message.add_reaction('➡️')
        # await results_message.add_reaction('❌')

        def reaction_check(reaction, user):
            allowed_emoji = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '⬅️', '➡️']
            return user.id == ctx.author.id and str(reaction.emoji) in allowed_emoji and reaction.message.id == results_message.id

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=25.0, check=reaction_check)
            await reaction.remove(user)

            beginning_index = 0
            end_index = 5
            reaction_string = str(reaction.emoji)
            while reaction_string == "⬅️" or reaction_string == "➡️":
                if reaction_string == "⬅️":
                    beginning_index -= 5
                    end_index -= 5
                    if beginning_index < 0:
                        beginning_index = 0
                        end_index = 5
                    await self.edit_results_post(results, results_message, beginning_index, end_index, japanese_input)
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=20.0, check=reaction_check)
                    await reaction.remove(user)
                    reaction_string = str(reaction.emoji)

                elif reaction_string == "➡️":
                    beginning_index += 5
                    end_index += 5
                    if beginning_index >= len(results):
                        beginning_index -= 5
                        end_index -= 5
                    await self.edit_results_post(results, results_message, beginning_index, end_index, japanese_input)
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=20.0, check=reaction_check)
                    await reaction.remove(user)
                    reaction_string = str(reaction.emoji)

                else:
                    await ctx.send("Unexpected error. Exiting...")

        except asyncio.TimeoutError:
            await ctx.send("Function timed out. Exiting...")
            return

        if str(reaction.emoji) == "1️⃣":
            result_index = beginning_index
        elif str(reaction.emoji) == "2️⃣":
            result_index = beginning_index + 1
        elif str(reaction.emoji) == "3️⃣":
            result_index = beginning_index + 2
        elif str(reaction.emoji) == "4️⃣":
            result_index = beginning_index + 3
        elif str(reaction.emoji) == "5️⃣":
            result_index = beginning_index + 4
        elif str(reaction.emoji) == '❌':
            await ctx.send("Exiting...")
            return
        else:
            await ctx.send("Exiting...")
            return

        try:
            relevant_result = results[result_index]
        except IndexError:
            await ctx.send("Invalid index. Exiting...")
            return

        await ctx.send("Creating video file...")

        content, beginning_time, end_time = await self.get_sub_timings(relevant_result[1], relevant_result[3])

        video_file_name = f"{relevant_result[1][:-3]}mkv"

        await self.download_file(video_file_name)
        await self.create_video(video_file_name, beginning_time, end_time)

        stripped_content = content.replace('\n', '　 ')

        video_file = discord.File(f"data/video/result_{video_file_name[:-3] + 'mp4'}")
        resultembed = discord.Embed(title=f"Result {result_index + 1} for {japanese_input}")
        resultembed.add_field(name="Text:", value=stripped_content, inline=False)

        await ctx.send(embed=resultembed, file=video_file)

        await asyncio.sleep(1)

        for file in os.listdir('data/video/'):
            if not file == "placerholder":
                os.remove(f'data/video/{file}')



def setup(bot):
    bot.add_cog(AnimeCog(bot))