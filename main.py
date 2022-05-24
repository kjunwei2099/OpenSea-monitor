import requests
import json
import time
import discord
from discord.ext import commands
import pytz
from dateutil import parser
import asyncio
from webserver import keep_alive
from os import system

# unused 1st

token2 = "YOUR DISCORD TOKEN"
bot = commands.Bot(
    command_prefix="!",  # bot prefix
    case_insensitive=True,  # case-sensitive
    intents=discord.Intents.all(),  # 特權網關意圖(接收特殊事件)
    help_command=None  # 禁用預設help指令
)

headers = {
    'Accept': 'application/json',
    'X-API-KEY': 'YOUR OPENSEA API'
}


def make_url(address, now, cursor):
    url = f"https://api.opensea.io/api/v1/events?only_opensea=true&asset_contract_address={address}&event_type=successful&occurred_after={now}&cursor={cursor}"
    return url


@bot.event
async def on_ready():
    while True:
        with open('contract_address.json', 'r') as cAddress:
            addressData = json.load(cAddress)
        now = str(time.time())
        now = now.split('.')[0]
        now = int(now) - 300

        for addresses in addressData:
            name = addresses['name']
            address = addresses['address']

            base_url = f'https://api.opensea.io/api/v1/events?only_opensea=true&asset_contract_address={address}&event_type=successful&occurred_after={now}'
            old = []
            oldHash = []
            try:
                with open(f'{address}.json', 'r') as f:
                    jdata = json.load(f)
                for item in jdata:
                    old.append(item)
                    oldHash.append((item['transaction']['transaction_hash']))
            except:
                pass

            new = []
            c = 1
            req = requests.get(base_url, headers=headers)
            r = req.json()
            if req.status_code == 200:
                if len(r['asset_events']) != 0:
                    for item in r['asset_events']:
                        new.append(item)
                    while c < 5:
                        try:
                            if r['next'] != None:
                                r = requests.get(make_url(address, now, r['next']), headers=headers).json()
                                for item in r['asset_events']:
                                    new.append(item)
                        except:
                            print("finish")
                        c += 1
                verify = False
                for item in new:
                    if item['transaction']['transaction_hash'] not in oldHash:
                        verify = True
                if verify == True:
                    channel = bot.get_channel(int(addresses['channel']))
                for asset_events in new:
                    if asset_events['transaction']['transaction_hash'] not in oldHash:
                        old.append(asset_events)
                        stats = requests.get(
                            f"https://api.opensea.io/api/v1/collection/{asset_events['collection_slug']}/stats").json()
                        print(stats)
                        floor_price = stats['stats']['floor_price']
                        try:
                            projectName = (asset_events['asset']['asset_contract']['name'])
                            opensea = "https://opensea.io/collection/" + asset_events['collection_slug']
                            image = asset_events['asset']['image_thumbnail_url']
                            tokenLink = asset_events['asset']['permalink']
                            seller = asset_events['seller']['address']
                            value = str("{:.4f} Eth".format(int(asset_events['total_price']) * (10 ** -18)))
                            hash = asset_events['transaction']['transaction_hash']
                            timestamp = asset_events['created_date']
                            buyer = asset_events['winner_account']['address']
                            tokenid = asset_events['asset']['token_id']
                        except TypeError:
                            print("Error")
                            print(asset_events['transaction']['transaction_hash'])
                        timezone = pytz.timezone('Asia/Kuala_Lumpur')
                        date = parser.parse(timestamp).astimezone(tz=timezone)
                        date = (date.strftime('%Y-%m-%d %I:%M:%S%p'))

                        hashLink = f"https://etherscan.io/tx/{hash}"
                        embed = discord.Embed(title=projectName, url=opensea, description=" ", color=0xe8006f)
                        if image is not None:
                            embed.set_thumbnail(url=image)
                        embed.add_field(name="Token ID", value=f"[{tokenid}]({tokenLink})", inline=False)
                        embed.add_field(name="Price", value=value, inline=False)
                        embed.add_field(name="Floor", value=floor_price, inline=False)
                        embed.add_field(name="Hash", value=f"[Hash Etherscan]({hashLink})", inline=False)
                        embed.add_field(name="Time", value=date, inline=False)
                        await channel.send(embed=embed)
                        await asyncio.sleep(1)

                with open(f'{address}.json', 'w') as f:
                    json.dump(old, f, indent=4)
                print("Done " + name)
                await asyncio.sleep(2)
            else:
                await asyncio.sleep(5)
                print("Server Error")


@bot.command()
async def nft_add(ctx, name, address, channelID):
    old = []
    with open('contract_address.json') as contractAddressFile:
        jdata = json.load(contractAddressFile)
    for item in jdata:
        old.append(item)

    store = {}
    store['name'] = name
    store['address'] = address
    store['channel'] = channelID
    if store not in old:
        old.append(store)
        await ctx.send("Address Added")
    with open('contract_address.json', 'w') as f:
        json.dump(old, f, indent=4)


@bot.command()
async def nft_list(ctx):
    with open('contract_address.json', 'r') as cAddress:
        addressData = json.load(cAddress)
    store = []
    count = 1
    for item in addressData:
        name = item['name']
        list = f'{str(count)}. {name} \n'
        store.append(list)
        count += 1
    x = ''.join(store)
    embed = discord.Embed(title="Monitor List", description=" ", color=0xe8006f)
    embed.add_field(name="List", value=x, inline=False)
    await ctx.send(embed=embed)


@bot.command()
async def nft_rem(ctx, name):
    list = []
    with open('contract_address.json') as contractAddressFile:
        jdata = json.load(contractAddressFile)
    for item in jdata:
        list.append(item)
    for item in list:
        if name != item['name']:
            pass
        else:
            list.remove(item)
            await ctx.send(f"{name} Removed from monitor")
    with open('contract_address.json', 'w') as f:
        json.dump(list, f, indent=4)


@bot.command()
async def floor(ctx, address):
    baseUrl = f'https://api.opensea.io/api/v1/asset_contract/{address}'
    r = requests.get(baseUrl, headers=headers).json()
    slug = r['collection']['slug']
    url = f'https://api.opensea.io/api/v1/collection/{slug}'

    r = requests.get(url, headers=headers).json()
    store = []
    data = {}
    data['url'] = "https://opensea.io/collection/" + slug
    for item in r['collection']['primary_asset_contracts']:
        data['name'] = item['name']
        data['image'] = item['image_url']
        data['supply'] = f"{(r['collection']['stats']['total_supply']):.0f}"
    data['average'] = f"{(r['collection']['stats']['average_price']):.2f} Eth"
    data['floor'] = f"{(r['collection']['stats']['floor_price']):.2f} Eth"

    embed = discord.Embed(title=data['name'], url=data['url'], description=" ", color=0xe8006f)
    embed.set_thumbnail(url=data['image'])
    embed.add_field(name="Total Supply", value=data['supply'], inline=False)
    embed.add_field(name="Average Sales", value=data['average'], inline=False)
    embed.add_field(name="Floor Price", value=data['floor'], inline=False)
    await ctx.send(embed=embed)


@bot.command()
async def nft_help(ctx):
    x = "!nft_add <ProjectName> <Contract Address> <Discord_Channel_ID>\n!nft_rem <ProjectName>\n!nft_list\n!floor <contract_address>"
    embed = discord.Embed(title="NFT Commands", description=" ", color=0xe8006f)
    embed.add_field(name="List", value=x, inline=False)
    await ctx.send(embed=embed)


@bot.command()
async def pingnft(ctx):
    await ctx.send('Pong! {0}'.format(round(bot.latency, 10)))


keep_alive()


def run():
    try:
        bot.run(token2)
    # except discord.errors.HTTPException:
    except:
        print("\n\n\nBLOCKED BY RATE LIMITS\nRESTARTING NOW\n\n\n")
        f = open("logs.txt", "a")
        f.write("Restart" + "\n")
        f.close()
        system("python restarter.py")
        system('kill 1')


while True:
    run()
    time.sleep(1800)
    print("Done")






