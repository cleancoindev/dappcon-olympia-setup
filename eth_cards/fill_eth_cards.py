import argparse
import logging
import os
import json
from ethereum.utils import checksum_encode, privtoaddr
from web3 import HTTPProvider, Web3
from web3.middleware import geth_poa_middleware

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def load_contract_interface(file_name):
    return _load_json_file(_abi_file_path(file_name))


def _abi_file_path(file):
    return os.path.abspath(os.path.join(os.path.dirname(__file__), file))


def _load_json_file(path):
    with open(path) as f:
        return json.load(f)


w3 = Web3(HTTPProvider('https://rinkeby.infura.io/gnosis'))
w3.middleware_stack.inject(geth_poa_middleware, layer=0)

OLY_ADDRESS = '0x979861dF79C7408553aAF20c01Cfb3f81CCf9341'
ETH_SPLITTER_ADDRESS = '0xf9D860abb551BCe9799f1D4Eee0267ACb568E93D'
TOKEN_SPLITTER_ADDRESS = '0xe1a567b650BC37BCF395003477FaAdA944a7Ab36'

OLY_ABI = load_contract_interface('contracts/OlympiaToken.json')
ETH_SPLITTER_ABI = load_contract_interface('contracts/EtherSplitter.json')
TOKEN_SPLITTER_ABI = load_contract_interface('contracts/TokenSplitter.json')

OLY_CONTRACT = w3.eth.contract(OLY_ADDRESS, abi=OLY_ABI['abi'])
ETH_SPLITTER_CONTRACT = w3.eth.contract(ETH_SPLITTER_ADDRESS, abi=ETH_SPLITTER_ABI['abi'])
TOKEN_SPLITTER_CONTRACT = w3.eth.contract(TOKEN_SPLITTER_ADDRESS, abi=TOKEN_SPLITTER_ABI['abi'])

OLY_PER_ADDRESS = 200
ETHER_PER_ADDRESS = w3.toWei(0.5, 'ether')

parser = argparse.ArgumentParser()
parser.add_argument("filename", help="File with ethereum addresses")
parser.add_argument("private_key", help="private key to fund the safes")
args = parser.parse_args()


def chunks(self, iterable, size=100):
    """
    Split a list of elements into lists of fixed size elements
    """
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]


def read_file(filename):
    with open(filename) as f:
        return [address.strip() for address in f]


def split_tokens(private_key: str, addresses: str, amount_per_address: int,
                 token_address: str):
    tx_hashes = []
    for address_sublist in chunks(addresses):
        tx = TOKEN_SPLITTER_CONTRACT.functions.splitTokens(address_sublist,
                                                           token_address,
                                                           amount_per_address).buildTransaction()
        signed = w3.eth.account.signTransaction(tx, private_key)
        tx_hashes.append(w3.eth.sendRawTransaction(signed.rawTransaction))
    return tx_hashes


def send_ether(private_key: str, address: str, total_value: int):
    public_key = checksum_encode(privtoaddr(private_key))
    tx = {
        'to': address,
        'value': total_value,
        'gas': 23000,
        'gasPrice': w3.eth.gasPrice,
        'nonce': w3.eth.getTransactionCount(public_key, 'pending'),
    }

    signed_tx = w3.eth.account.signTransaction(tx, private_key=private_key)
    return w3.eth.sendRawTransaction(signed_tx.rawTransaction)


def split_ether(private_key: str, addresses: str):
    tx_hashes = []
    for address_sublist in chunks(addresses):
        tx = ETH_SPLITTER_CONTRACT.functions.splitEther(address_sublist).buildTransaction()
        signed = w3.eth.account.signTransaction(tx, private_key)
        tx_hashes.append(w3.eth.sendRawTransaction(signed.rawTransaction))
    return tx_hashes


filename = args.filename
private_key = args.private_key

addresses = read_file(filename)
send_ether(private_key, ETH_SPLITTER_ADDRESS, len(addresses) * ETHER_PER_ADDRESS)
split_ether(private_key, addresses)
OLY_CONTRACT.approve(TOKEN_SPLITTER_ADDRESS, len(addresses) * OLY_PER_ADDRESS)
split_tokens(private_key, addresses, OLY_PER_ADDRESS, OLY_ADDRESS)
