"""
Written by NueCD.
License GPLv3.
Tutorial by https://python.land/build-discord-bot-in-python-that-plays-music
"""

from time import sleep
import asyncio
import discord
from discord.ext import commands, tasks
import youtube_dl

"""
Init bot stuff.
"""
TOKEN = ''
PREFIX = ''

intents = discord.Intents.default()
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix=PREFIX, intents=intents)
song_queue = []

"""
Init youtube_dl stuff.
"""
youtube_dl.utils.bug_reports_message = ''
base_volume = '0.5'
ffmpeg_options = { 'options': '-vn' }
ytdl_format_options = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

"""
Does this really need to be a class? I hate classes.
I have no idea how this works...
"""
class PlayerSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=base_volume):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = ''

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        # wtf is this
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        
        if 'entries' in data:
            return 'playlist'

        # Don'r allow livestreams.
        if data['is_live']:
            return 'is_live'

        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        
        filename = ytdl.prepare_filename(data)
        return [data['title'], filename]

# Play the queue and leave efter a while.
async def start_playing(ctx, voice):
        while len(song_queue):
            time = 0
            song = song_queue.pop(0)
            voice.play(discord.FFmpegPCMAudio(executable='ffmpeg', source=song[1]))
            await ctx.send('Now playing: %s' % song[0])
            while voice.is_playing():
                await asyncio.sleep(1)

# Auto leave after some time.                
async def auto_leave(voice):
    time = 0
    while 1:
        if voice.is_playing():
            time = 0
        else:
            time += 1
            if time > 300:
                await voice.disconnect()
                return
        await asyncio.sleep(1)
       
"""
Commands.
"""
# Join voice channel.
@bot.command(name='join', help='Join the voice channel.')
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send('%s is not in voice. Where do I go?' % ctx.message.author.name)
        return 1
    
    await ctx.message.author.voice.channel.connect()
    await ctx.send('The bot needs to download songs before playing them. If you queue something long the bot will be busy for a while and fill my server with large files.\nPlease use with respect.\n\nUse command $help for instructions.')
    
    voice = ctx.message.guild.voice_client
    auto_leaver = asyncio.create_task(auto_leave(voice))

# Leave voice channel.
@bot.command(name='leave', help='Leave the voice channel.')
async def leave(ctx):
    voice = ctx.message.guild.voice_client
    if voice:
        await voice.disconnect()
        song_queue = []
    else:
        await ctx.send('Not in voice atm.')

# Play a song.
@bot.command(name='play', help='Play an url.')
async def play(ctx, url):
    voice = ctx.message.guild.voice_client
    
    # Check if we are in voice.
    if not voice:
        await ctx.send('Use join command first.')
        return

    # Check if the person queueing songs are in voice.
    if not ctx.message.author.voice:
        await ctx.send('You must be in a voice channel to play.')
        return

    # Check if we are connected to voice without issues.
    if not voice.is_connected():
        await ctx.send('Voice is not connected properly. Probably issues connecting to voice...')
        return
    
    if not 'youtu' in url:
        await ctx.send('This does not look like a youtube link.')
        return

    # Playlists are not supported.
    if 'list=' in url:
        await ctx.send('This is a playlist. Currently not supporting this.')
        return
        
    # Start looking for the song and add it to queue.
    async with ctx.typing():
        song = await PlayerSource.from_url(url, loop=bot.loop)
        
        # No support for livestreams-
        if song == 'is_live':
            await ctx.send('This is a livestream. Currently not supporting this.')
            return

        # No support for playlists.
        if song == 'playlist':
            await ctx.send('This is a playlist. Currently not supporting this.')
            return

        song_queue.append(song)
        await ctx.send('Added to queue: %s' % song[0])
    
    # Start the player in the background if it is not running.
    if not voice.is_playing():
        player = asyncio.create_task(start_playing(ctx, voice))

# Show the queue
@bot.command(name='queue', help='Show the queue.')
async def queue(ctx):
    if len(song_queue):
        await ctx.send('Queue:\n' + '\n'.join(song_queue))
    else:
        await ctx.send('Queue is empty.')

# Skip song.
@bot.command(name='skip', help='Stop playing track.')
async def skip(ctx):
    voice = ctx.message.guild.voice_client

    if voice:
        if voice.is_playing():
            voice.stop()

"""
Start the bot.
"""
bot.run(TOKEN)
