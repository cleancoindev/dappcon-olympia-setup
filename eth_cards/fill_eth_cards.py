import argparse
import logging

from ethereum.utils import checksum_encode, privtoaddr
from web3 import HTTPProvider, Web3
from web3.middleware import geth_poa_middleware
import settings
from utils import load_contract_interface, read_addresses_from_file

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


w3 = Web3(HTTPProvider(settings.NODE_URL))
w3.middleware_stack.inject(geth_poa_middleware, layer=0)

OLY_ABI = load_contract_interface('contracts/OlympiaToken.json')
STANDARD_TOKEN_ABI = load_contract_interface('contracts/StandardToken.json')
ETH_SPLITTER_ABI = load_contract_interface('contracts/EtherSplitter.json')
TOKEN_SPLITTER_ABI = load_contract_interface('contracts/TokenSplitter.json')

OLY_CONTRACT = w3.eth.contract(settings.OLY_ADDRESS, abi=OLY_ABI['abi'])
RDN_CONTRACT = w3.eth.contract(settings.RDN_ADDRESS, abi=STANDARD_TOKEN_ABI['abi'])
ETH_SPLITTER_CONTRACT = w3.eth.contract(settings.ETH_SPLITTER_ADDRESS, abi=ETH_SPLITTER_ABI['abi'])
TOKEN_SPLITTER_CONTRACT = w3.eth.contract(settings.TOKEN_SPLITTER_ADDRESS, abi=TOKEN_SPLITTER_ABI['abi'])

OLY_PER_ADDRESS = w3.toWei(1, 'ether')
ETHER_PER_ADDRESS = w3.toWei(0.0001, 'ether')
RDN_PER_ADDRESS = w3.toWei(1, 'ether')

parser = argparse.ArgumentParser()
parser.add_argument("filename", help="File with ethereum addresses")
parser.add_argument("private_key", help="private key to fund the safes")
args = parser.parse_args()

filename = args.filename
private_key = args.private_key
public_key = checksum_encode(privtoaddr(private_key))


def chunks(iterable, size=100):
    """
    Split a list of elements into lists of fixed size elements
    """
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]


def split_tokens(addresses: str, amount_per_address: int,
                 token_address: str):
    tx_hashes = []
    for address_sublist in chunks(addresses):
        tx = TOKEN_SPLITTER_CONTRACT.functions.splitTokens(address_sublist,
                                                           token_address,
                                                           amount_per_address
                                                           ).buildTransaction(
            {'nonce': w3.eth.getTransactionCount(public_key, 'pending'), 'gas': settings.GAS_LIMIT,
             'gasPrice': settings.GAS_PRICE})
        signed = w3.eth.account.signTransaction(tx, private_key)
        tx_hash = w3.eth.sendRawTransaction(signed.rawTransaction)
        print('split RDN - {}/tx/{}'.format(settings.ETHERSCAN_URL, tx_hash.hex()))
        tx_hashes.append(tx_hash)
    return tx_hashes


def issue_oly(addresses: str, amount_per_address: int):
    tx_hashes = []
    for address_sublist in chunks(addresses):
        tx = OLY_CONTRACT.functions.issue(address_sublist, amount_per_address).buildTransaction(
            {'nonce': w3.eth.getTransactionCount(public_key, 'pending'), 'gas': settings.GAS_LIMIT,
             'gasPrice': settings.GAS_PRICE}
        )
        signed = w3.eth.account.signTransaction(tx, private_key)
        tx_hash = w3.eth.sendRawTransaction(signed.rawTransaction)
        print ('issue oly - {}/tx/{}'.format(settings.ETHERSCAN_URL, tx_hash.hex()))
        tx_hashes.append(tx_hash)
    return tx_hashes


def split_ether(addresses: str, total_value: int):
    tx_hashes = []

    for address_sublist in chunks(addresses):
        tx = ETH_SPLITTER_CONTRACT.functions.splitEther(address_sublist).buildTransaction(
            {'value': total_value, 'nonce': w3.eth.getTransactionCount(public_key, 'pending'),
             'gas': settings.GAS_LIMIT, 'gasPrice': settings.GAS_PRICE}
        )
        signed = w3.eth.account.signTransaction(tx, private_key)
        tx_hash = w3.eth.sendRawTransaction(signed.rawTransaction)
        print ('split ether - {}/tx/{}'.format(settings.ETHERSCAN_URL, tx_hash.hex()))
        tx_hashes.append(tx_hash)
    return tx_hashes


def approve_token(contract, address: str, amount: int):

    tx = contract.functions.approve(address, amount).buildTransaction(
        {'nonce': w3.eth.getTransactionCount(public_key, 'pending')}
    )
    signed = w3.eth.account.signTransaction(tx, private_key)
    tx_hash = w3.eth.sendRawTransaction(signed.rawTransaction)
    print ('approve tokens - https://rinkeby.etherscan.io/tx/{}'.format(tx_hash.hex()))
    w3.eth.waitForTransactionReceipt(tx_hash)
    return tx_hash


addresses = read_addresses_from_file(filename)

print('Setting up {} participant eth-cards'.format(len(addresses)))

approve_token(RDN_CONTRACT, settings.TOKEN_SPLITTER_ADDRESS, len(addresses) * RDN_PER_ADDRESS)
split_ether(addresses, len(addresses) * ETHER_PER_ADDRESS)
split_tokens(addresses, RDN_PER_ADDRESS, settings.RDN_ADDRESS)
issue_oly(addresses, OLY_PER_ADDRESS)
