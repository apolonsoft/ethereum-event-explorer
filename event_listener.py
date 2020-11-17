import asyncio
import json

import traceback
from pprint import pformat
from configparser import ConfigParser

from dynaconf import settings
from loguru import logger
from web3 import Web3, WebsocketProvider
from web3._utils.events import construct_event_topic_set, get_event_data
from web3.exceptions import LogTopicError

from app.enums import Currency

import nest_asyncio
nest_asyncio.apply()


NETWORK_ID = settings.NETWORK_ID
print(settings.NETWORKS[NETWORK_ID].NODE_URL)
W3 = Web3(WebsocketProvider(settings.NETWORKS[NETWORK_ID].NODE_URL))

async def load_event_signatures():
    tracked_events = {}

    def prepare_events(contract):
        with open(contract['abi'], 'r') as file:
            abi = json.loads(file.read())
            for element in abi:
                if element['type'] == 'event':
                    topic = construct_event_topic_set(element)[0]
                    if element['name'] in contract['tracked_event_names']:
                        if topic not in tracked_events:
                            tracked_events[topic] = element
                            logger.info(f'Added event {contract["abi"]} - {element["name"]}')
                        if 'addresses' not in tracked_events[topic]:
                            tracked_events[topic]['addresses'] = []
                        tracked_events[topic]['addresses'].append(contract['address'])

    prepare_events(settings.NETWORKS[NETWORK_ID].ETH_CONTRACT)
    prepare_events(settings.NETWORKS[NETWORK_ID].USDT_CONTRACT)

    return tracked_events


async def process_event(event, network_id):
    logger.info(f"\r\n{event.event} - {event.address}\r\n{pformat(dict(event.args))}")
    payload = {
        key.replace("_", ""): value.hex() if isinstance(value, bytes) else value
        for key, value in event.args.items()
    }
    currency = None

    if event.address.lower() == settings.NETWORKS[NETWORK_ID].ETH_CONTRACT['address'].lower():
        currency = Currency.ETH
    if event.address.lower() == settings.NETWORKS[NETWORK_ID].USDT_CONTRACT['address'].lower():
        currency = Currency.USDT

    payload.update({
        'network_id': network_id,
        'transaction_hash': event.transactionHash.hex(),
        'name': event.event,
        'block': event.blockNumber,
        'address': event.address,
        'currency': currency
    })
    logger.error(f"You can process data here")


async def main():
    global W3
    config_filename = f'listener_network_{NETWORK_ID}.ini'
    config = ConfigParser()
    config.read(config_filename)
    if not config.has_section('default'):
        config.add_section('default')
    if not config.has_option('default', 'last_block_number'):
        config.set('default', 'last_block_number', str(W3.eth.blockNumber - 1))
    with open(config_filename, 'w') as f:
        config.write(f)
    last_block_number = int(config.get('default', 'last_block_number'))
    tracked_events = await load_event_signatures()

    while True:
        try:
            latest_block = W3.eth.blockNumber

            if latest_block > last_block_number:
                network_id = W3.eth.chainId
                logger.info(f'Block {last_block_number + 1}')

                log_items = W3.eth.filter({
                    'fromBlock': last_block_number + 1,
                    'toBlock': last_block_number + 1
                }).get_all_entries()
                for log_item in log_items:
                    for topic in log_item['topics']:
                        if topic.hex() in tracked_events:
                            try:
                                parsed_event = get_event_data(tracked_events[topic.hex()], log_item)
                                if parsed_event['address'] in tracked_events[topic.hex()]['addresses']:
                                    await process_event(parsed_event, network_id)
                            except LogTopicError:
                                logger.debug('Bad event')
                config.set('default', 'last_block_number', str(last_block_number + 1))
                with open(config_filename, 'w') as f:
                    config.write(f)
                last_block_number += 1
        except:
            logger.error(traceback.format_exc())
            W3 = Web3(WebsocketProvider(settings.NETWORKS[NETWORK_ID].NODE_URL))
            await asyncio.sleep(settings.DELAY)
        finally:
            if latest_block <= last_block_number:
                await asyncio.sleep(settings.DELAY)


asyncio.get_event_loop().run_until_complete(main())
