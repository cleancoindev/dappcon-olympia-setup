from utils import read_addresses_from_file, load_contract_interface
import argparse
from web3 import HTTPProvider, Web3
from web3.middleware import geth_poa_middleware
import settings

parser = argparse.ArgumentParser()
parser.add_argument("filename", help="File with ethereum addresses")
args = parser.parse_args()

filename = args.filename

w3 = Web3(HTTPProvider(settings.NODE_URL))
w3.middleware_stack.inject(geth_poa_middleware, layer=0)

addresses = read_addresses_from_file(filename)

STANDARD_TOKEN_ABI = load_contract_interface('contracts/StandardToken.json')

OLY_CONTRACT = w3.eth.contract(settings.OLY_ADDRESS, abi=STANDARD_TOKEN_ABI['abi'])
RDN_CONTRACT = w3.eth.contract(settings.RDN_ADDRESS, abi=STANDARD_TOKEN_ABI['abi'])

for address in addresses:
    oly_balance = OLY_CONTRACT.functions.balanceOf(address).call()/1e18
    rdn_balance = RDN_CONTRACT.functions.balanceOf(address).call()/1e18
    eth_balance = w3.eth.getBalance(address)/1e18
    print('{:42} {:04} OLY - {:04} RDN - {:04} ETH'.format(address, oly_balance, rdn_balance, eth_balance))